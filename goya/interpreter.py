# -*- coding: utf-8 -*-
"""مفسر گویا: اجرای درخت برنامه (tree-walking)"""

import time

from .errors import GoyaPropError, GoyaRuntimeError
from .parser import (
    Assign, Attr, AttrAssign, Bin, Break, Call, Const, Continue, ExprStmt,
    ForIn, ForRange, FuncDef, If, Index, ListLit, Name, Num, Return, Str, Un,
    While,
)
from .stdlib import Builtin, install_builtins


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class Env:
    """محیط متغیرها — زنجیره‌ای (محلی → والد → ...)"""

    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def _find(self, name):
        e = self
        while e is not None:
            if name in e.vars:
                return e
            e = e.parent
        return None

    def define(self, name, value):
        self.vars[name] = value

    def get(self, name, line=None):
        e = self._find(name)
        if e is None:
            raise GoyaRuntimeError(
                'متغیر «{}» تعریف نشده — اول با = بهش مقدار بده'.format(name), line
            )
        return e.vars[name]

    def assign(self, name, value, line=None):
        e = self._find(name)
        if e is None:
            # مغازه‌داری ساده: اگه جای دیگه‌ای نیست، همین‌جا تعریفش می‌کنیم
            self.vars[name] = value
        else:
            e.vars[name] = value


class Function:
    """تابع تعریف‌شده در خود گویا"""

    def __init__(self, name, params, body, closure):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure


class Interpreter:
    def __init__(self, input_fn=None, time_limit=10.0):
        self.global_env = Env()
        install_builtins(self.global_env, input_fn=input_fn)
        self.time_limit = time_limit
        self._started = time.monotonic()
        self._steps = 0

    def reset_clock(self):
        """شروع دوباره‌ی ساعت محافظ — برای REPL که با یک مفسر چند ورودی اجرا می‌شه"""
        self._started = time.monotonic()
        self._steps = 0

    def _check_time(self):
        if self.time_limit is not None:
            if time.monotonic() - self._started > self.time_limit:
                raise GoyaRuntimeError(
                    "برنامه زیادی طول کشید — حلقه بی‌نهایت گرفتی؟"
                )

    def run(self, program):
        self.reset_clock()
        try:
            for st in program.statements:
                self.exec_stmt(st, self.global_env)
        except BreakSignal:
            raise GoyaRuntimeError("«بشکن» فقط داخل حلقه معنی داره")
        except ContinueSignal:
            raise GoyaRuntimeError("«ادامه» فقط داخل حلقه معنی داره")
        from .gui import finish_gui_if_active
        finish_gui_if_active(self)

    def evaluate(self, expr, env=None):
        return self.eval_expr(expr, env or self.global_env)

    # ─── اجرای دستورها ───

    def exec_stmt(self, st, env):
        self._steps += 1
        if self._steps % 2048 == 0:
            self._check_time()
        if isinstance(st, ExprStmt):
            self.eval_expr(st.expr, env)
        elif isinstance(st, Assign):
            value = self.eval_expr(st.expr, env)
            env.assign(st.name, value, st.line)
            tag = getattr(value, "goya_set_name", None)
            if callable(tag):
                tag(st.name)
        elif isinstance(st, AttrAssign):
            obj = self.eval_expr(st.obj, env)
            self._set_attr(obj, st.name, self.eval_expr(st.expr, env), st.line)
        elif isinstance(st, If):
            self._exec_if(st, env)
        elif isinstance(st, While):
            self._exec_while(st, env)
        elif isinstance(st, ForRange):
            self._exec_for_range(st, env)
        elif isinstance(st, ForIn):
            self._exec_for_in(st, env)
        elif isinstance(st, FuncDef):
            env.define(st.name, Function(st.name, st.params, st.body, env))
        elif isinstance(st, Return):
            value = self.eval_expr(st.value, env) if st.value is not None else None
            raise ReturnSignal(value)
        elif isinstance(st, Break):
            raise BreakSignal()
        elif isinstance(st, Continue):
            raise ContinueSignal()
        else:
            raise GoyaRuntimeError("دستور ناشناخته", getattr(st, "line", None))

    def _exec_if(self, st, env):
        if self._truthy(self.eval_expr(st.cond, env)):
            self._exec_block(st.then, env)
            return
        for cond, body in st.elifs:
            if self._truthy(self.eval_expr(cond, env)):
                self._exec_block(body, env)
                return
        if st.els is not None:
            self._exec_block(st.els, env)

    def _exec_while(self, st, env):
        while self._truthy(self.eval_expr(st.cond, env)):
            try:
                self._exec_block(st.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_for_range(self, st, env):
        start = self.eval_expr(st.start, env)
        end = self.eval_expr(st.end, env)
        if not self._is_int(start) or not self._is_int(end):
            raise GoyaRuntimeError("حدود حلقه «از ... تا ...» باید عدد صحیح باشه", st.line)
        for i in range(start, end + 1):
            env.define(st.var, i)
            try:
                self._exec_block(st.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_for_in(self, st, env):
        iterable = self.eval_expr(st.iterable, env)
        if isinstance(iterable, str):
            items = list(iterable)
        elif isinstance(iterable, list):
            items = iterable
        else:
            raise GoyaRuntimeError(
                "حلقه «در» فقط با لیست و متن کار می‌کنه", st.line
            )
        for item in items:
            env.define(st.var, item)
            try:
                self._exec_block(st.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def _exec_block(self, stmts, env):
        for st in stmts:
            self.exec_stmt(st, env)

    # ─── ارزیابی عبارت‌ها ───

    def eval_expr(self, e, env):
        if isinstance(e, Num):
            return e.value
        if isinstance(e, Str):
            return e.value
        if isinstance(e, Const):
            return e.value
        if isinstance(e, Name):
            return env.get(e.name, e.line)
        if isinstance(e, ListLit):
            return [self.eval_expr(item, env) for item in e.items]
        if isinstance(e, Un):
            return self._eval_un(e, env)
        if isinstance(e, Bin):
            return self._eval_bin(e, env)
        if isinstance(e, Call):
            return self._eval_call(e, env)
        if isinstance(e, Index):
            return self._eval_index(e, env)
        if isinstance(e, Attr):
            obj = self.eval_expr(e.obj, env)
            return self._get_attr(obj, e.name, e.line)
        raise GoyaRuntimeError("عبارت ناشناخته")

    def _get_attr(self, obj, name, line=None):
        getter = getattr(obj, "goya_get", None)
        if callable(getter):
            try:
                return getter(name)
            except GoyaPropError as e:
                raise GoyaRuntimeError(str(e), line)
        raise GoyaRuntimeError(
            "این مقدار ویژگی «{}» نداره".format(name), line
        )

    def _set_attr(self, obj, name, value, line=None):
        setter = getattr(obj, "goya_set", None)
        if callable(setter):
            try:
                setter(name, value)
                return
            except GoyaPropError as e:
                raise GoyaRuntimeError(str(e), line)
        raise GoyaRuntimeError(
            "به این مقدار نمی‌شه ویژگی «{}» داد".format(name), line
        )

    def _eval_un(self, e, env):
        v = self.eval_expr(e.operand, env)
        if e.op == "-":
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise GoyaRuntimeError("منفی کردن فقط برای عدد کار می‌کنه", e.line)
            return -v
        if e.op == "نه":
            return not self._truthy(v)
        raise GoyaRuntimeError("عملگر ناشناخته", e.line)

    def _eval_bin(self, e, env):
        # و / یا: ارزیابی کوتاه
        if e.op == "و":
            return self._truthy(self.eval_expr(e.left, env)) and \
                self._truthy(self.eval_expr(e.right, env))
        if e.op == "یا":
            return self._truthy(self.eval_expr(e.left, env)) or \
                self._truthy(self.eval_expr(e.right, env))

        left = self.eval_expr(e.left, env)
        right = self.eval_expr(e.right, env)

        if e.op == "+":
            return self._op_plus(left, right, e.line)
        if e.op in ("-", "*", "/", "%"):
            return self._op_arith(e.op, left, right, e.line)
        if e.op in ("==", "!="):
            eq = self._is_int(left) and self._is_int(right)
            eq = eq or (type(left) is type(right))
            result = left == right if eq else False
            return result if e.op == "==" else not result
        if e.op in ("<", "<=", ">", ">="):
            return self._op_compare(e.op, left, right, e.line)
        raise GoyaRuntimeError("عملگر ناشناخته", e.line)

    def _op_plus(self, left, right, line):
        if self._is_num(left) and self._is_num(right):
            return left + right
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        if isinstance(left, list) and isinstance(right, list):
            return left + right
        if (isinstance(left, str) and not isinstance(right, str)) or \
           (isinstance(right, str) and not isinstance(left, str)):
            raise GoyaRuntimeError(
                "متن و عدد رو نمی‌شه با + چسبوند — از متن() استفاده کن: متن({})".format(
                    "رشته" if isinstance(right, str) else "عدد"
                ),
                line,
            )
        raise GoyaRuntimeError("این دو تا نوع با + جمع نمی‌شن", line)

    def _op_arith(self, op, left, right, line):
        if not self._is_num(left) or not self._is_num(right):
            raise GoyaRuntimeError(
                "عملگر «{}» فقط بین دو عدد کار می‌کنه".format(op), line
            )
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise GoyaRuntimeError("تقسیم بر صفر ممکن نیست", line)
            return left / right
        if op == "%":
            if right == 0:
                raise GoyaRuntimeError("باقیمانده بر صفر ممکن نیست", line)
            return left % right
        raise GoyaRuntimeError("عملگر ناشناخته", line)

    def _op_compare(self, op, left, right, line):
        both_num = self._is_num(left) and self._is_num(right)
        both_str = isinstance(left, str) and isinstance(right, str)
        if not (both_num or both_str):
            raise GoyaRuntimeError(
                "مقایسه‌ی ترتیبی فقط بین دو عدد یا دو متن ممکنه", line
            )
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        return left >= right

    def call_function(self, func, args, line=None):
        """فراخوانی مستقیم یک مقدار تابع — موتور GUI برای رویدادها استفاده می‌کنه"""
        if isinstance(func, Function):
            if len(args) != len(func.params):
                raise GoyaRuntimeError(
                    'تابع «{}» به {} ورودی نیاز داره ولی {} تا داده شد'.format(
                        func.name, self._fa(len(func.params)), self._fa(len(args))
                    ), line,
                )
            call_env = Env(func.closure)
            for pname, value in zip(func.params, args):
                call_env.define(pname, value)
            try:
                self._exec_block(func.body, call_env)
            except ReturnSignal as r:
                return r.value
            except BreakSignal:
                raise GoyaRuntimeError(
                    "«بشکن» داخل تابع، بیرون از حلقه‌ست", line
                )
            except ContinueSignal:
                raise GoyaRuntimeError(
                    "«ادامه» داخل تابع، بیرون از حلقه‌ست", line
                )
            return None
        if isinstance(func, Builtin):
            try:
                return func.fn(args)
            except GoyaRuntimeError as err:
                if err.line is None:
                    err.line = line
                raise
        raise GoyaRuntimeError("این یه تابع نیست که بشه صدا زد", line)

    def _eval_call(self, e, env):
        func = self.eval_expr(e.func, env)
        args = [self.eval_expr(a, env) for a in e.args]
        return self.call_function(func, args, e.line)

    def _eval_index(self, e, env):
        obj = self.eval_expr(e.obj, env)
        idx = self.eval_expr(e.idx, env)
        if not self._is_int(idx):
            raise GoyaRuntimeError("ایندکس باید عدد صحیح باشه", e.line)
        if isinstance(obj, (str, list)):
            try:
                return obj[idx]
            except IndexError:
                raise GoyaRuntimeError(
                    "ایندکس خارج از محدوده‌ست (طول: {})".format(self._fa(len(obj))),
                    e.line,
                )
        raise GoyaRuntimeError("ایندکس فقط برای لیست و متن کار می‌کنه", e.line)

    # ─── کمکی‌ها ───

    def _truthy(self, v):
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, (str, list)):
            return len(v) > 0
        return True

    def _is_num(self, v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def _is_int(self, v):
        return isinstance(v, int) and not isinstance(v, bool)

    def _fa(self, n):
        from .normalize import to_persian_digits
        return to_persian_digits(str(n))
