# -*- coding: utf-8 -*-
"""پارسر گویا: توکن‌ها → درخت برنامه (AST)

بلوک‌ها با تورفتگی مشخص می‌شن (بدون آکولاد و دونقطه — دونقطه اختیاری قبوله).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .errors import GoyaSyntaxError, IncompleteInput
from .normalize import strip_zwnj


# ─── گره‌های عبارت ───

@dataclass
class Num:
    value: object


@dataclass
class Str:
    value: str


@dataclass
class Const:
    value: object  # True / False / None (درست / غلط / پوچ)


@dataclass
class Name:
    name: str
    line: int


@dataclass
class Bin:
    op: str
    left: object
    right: object
    line: int


@dataclass
class Un:
    op: str  # '-' یا 'نه'
    operand: object
    line: int


@dataclass
class Call:
    func: "Name"
    args: List[object]
    line: int


@dataclass
class Index:
    obj: object
    idx: object
    line: int


@dataclass
class ListLit:
    items: List[object]
    line: int


# ─── گره‌های دستوری ───

@dataclass
class Assign:
    name: str
    expr: object
    line: int


@dataclass
class ExprStmt:
    expr: object


@dataclass
class If:
    cond: object
    then: List[object]
    elifs: List[Tuple[object, List[object]]]
    els: Optional[List[object]]


@dataclass
class While:
    cond: object
    body: List[object]


@dataclass
class ForRange:
    var: str
    start: object
    end: object
    body: List[object]
    line: int


@dataclass
class ForIn:
    var: str
    iterable: object
    body: List[object]
    line: int


@dataclass
class FuncDef:
    name: str
    params: List[str]
    body: List[object]
    line: int


@dataclass
class Return:
    value: object
    line: int


@dataclass
class Break:
    line: int


@dataclass
class Continue:
    line: int


@dataclass
class Program:
    statements: List[object]


# ─── کلیدواژه‌ها ───

CONSTANTS = {"درست": True, "غلط": False, "پوچ": None}

# کلماتی که نمی‌شن اسم متغیر یا تابع باشن
RESERVED = {
    "اگر", "وگرنه", "تا وقتی که", "برای هر", "برای", "هر", "از", "تا", "در",
    "تابع", "برگردان", "بشکن", "ادامه", "و", "یا", "نه", "وقتی", "که",
    "برابر", "نابرابر", "ضربدر", "تقسیم بر", "باقیمانده",
    "بزرگتر", "کوچکتر", "مساوی", "بزرگتر از", "کوچکتر از",
    "بزرگتر مساوی", "کوچکتر مساوی",
}

CMP_OPS = {
    "==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">=",
    "برابر": "==", "نابرابر": "!=",
    "بزرگتر از": ">", "کوچکتر از": "<",
    "بزرگتر مساوی": ">=", "کوچکتر مساوی": "<=",
}

MUL_OPS = {
    "*": "*", "/": "/", "%": "%",
    "ضربدر": "*", "تقسیم بر": "/", "باقیمانده": "%",
}


class Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    # ─── ابزارهای توکن ───

    def peek(self, offset=0):
        j = min(self.i + offset, len(self.toks) - 1)
        return self.toks[j]

    def advance(self):
        t = self.toks[self.i]
        if t.type != "EOF":
            self.i += 1
        return t

    def kw(self, tok):
        """کلیدواژه‌ی یک توکن NAME (بدون نیم‌فاصله)"""
        if tok.type == "NAME":
            return strip_zwnj(tok.value)
        return None

    def at_kw(self, word):
        return self.kw(self.peek()) == word

    def eat_kw(self, word):
        if self.at_kw(word):
            self.advance()
            return True
        return False

    def at_op(self, op):
        t = self.peek()
        return t.type == "OP" and t.value == op

    def eat_op(self, op):
        if self.at_op(op):
            self.advance()
            return True
        return False

    def error(self, msg, tok=None):
        t = tok or self.peek()
        raise GoyaSyntaxError(msg, t.line if t.type != "EOF" else None)

    # ─── برنامه ───

    def parse(self):
        stmts = []
        self._skip_newlines()
        while self.peek().type != "EOF":
            if self.peek().type == "DEDENT":
                self.advance()  # بستن خودکار انتهای فایل
                continue
            stmts.append(self.statement())
            self._skip_newlines()
        return Program(stmts)

    def _skip_newlines(self):
        while self.peek().type == "NEWLINE":
            self.advance()

    # ─── دستورها ───

    def statement(self):
        if self.at_kw("اگر"):
            return self.if_statement()
        if self.at_kw("تا وقتی که"):
            return self.while_statement()
        if self.at_kw("برای هر"):
            return self.for_statement()
        if self.at_kw("تابع"):
            return self.func_statement()
        if self.at_kw("برگردان"):
            return self.return_statement()
        if self.at_kw("بشکن"):
            tok = self.advance()
            self._end_of_line()
            return Break(tok.line)
        if self.at_kw("ادامه"):
            tok = self.advance()
            self._end_of_line()
            return Continue(tok.line)

        # انتساب یا عبارت
        line = self.peek().line
        e = self.expression()
        if self.at_op("="):
            self.advance()
            if not isinstance(e, Name):
                self.error("سمت چپ «=» باید یه اسم باشه")
            value = self.expression()
            self._end_of_line()
            return Assign(e.name, value, line)
        self._end_of_line()
        return ExprStmt(e)

    def _end_of_line(self):
        t = self.peek()
        if t.type == "NEWLINE":
            self.advance()
        elif t.type == "EOF":
            return
        else:
            self.error("انتهای این سطر نامفهومه")

    def _allow_colon(self):
        self.eat_op(":")

    def _block(self, header_line):
        t = self.peek()
        if t.type == "EOF":
            raise IncompleteInput("بدنه‌ی بلوک ناتمام مونده", header_line)
        if t.type != "NEWLINE":
            self.error("بعد از این سطر باید سطر تورفته (بدنه بلوک) بیاد")
        self.advance()
        t = self.peek()
        if t.type == "EOF":
            raise IncompleteInput("بدنه‌ی بلوک ناتمام مونده", header_line)
        if t.type != "INDENT":
            self.error("بدنه‌ی بلوک باید تورفته باشه")
        self.advance()
        stmts = []
        self._skip_newlines()
        while self.peek().type not in ("DEDENT", "EOF"):
            stmts.append(self.statement())
            self._skip_newlines()
        if self.peek().type == "EOF":
            raise IncompleteInput("بلوک بسته نشده — تورفتگی کمتر کن یا سطر بده", header_line)
        self.advance()  # DEDENT
        if not stmts:
            self.error("بدنه‌ی بلوک خالیه — حداقل یه سطر لازمه", self.toks[max(0, self.i - 1)])
        return stmts

    def if_statement(self):
        tok = self.advance()  # اگر
        cond = self.expression()
        self._allow_colon()
        then = self._block(tok.line)
        elifs = []
        els = None
        while self.at_kw("وگرنه"):
            self.advance()
            if self.at_kw("اگر"):
                etok = self.advance()
                c2 = self.expression()
                self._allow_colon()
                b2 = self._block(etok.line)
                elifs.append((c2, b2))
            else:
                etok = self.peek()
                els = self._block(etok.line)
                break
        return If(cond, then, elifs, els)

    def while_statement(self):
        self.advance()  # تا وقتی که
        cond = self.expression()
        self._allow_colon()
        body = self._block(self.peek().line)
        return While(cond, body)

    def for_statement(self):
        tok = self.advance()  # برای هر
        vt = self.peek()
        if vt.type != "NAME" or self.kw(vt) in RESERVED:
            self.error('بعد از «برای هر» باید یه اسم متغیر بیاد')
        var = self.advance().value
        if self.at_kw("از"):
            self.advance()
            start = self.expression()
            if not self.eat_kw("تا"):
                self.error('بعد از شروع بازه، کلمه‌ی «تا» لازمه')
            end = self.expression()
            self._allow_colon()
            body = self._block(tok.line)
            return ForRange(var, start, end, body, tok.line)
        if self.at_kw("در"):
            self.advance()
            iterable = self.expression()
            self._allow_colon()
            body = self._block(tok.line)
            return ForIn(var, iterable, body, tok.line)
        self.error('بعد از اسم حلقه، «از» یا «در» لازمه')

    def func_statement(self):
        tok = self.advance()  # تابع
        nt = self.peek()
        if nt.type != "NAME" or self.kw(nt) in RESERVED:
            self.error('بعد از «تابع» باید یه اسم تابع بیاد')
        name = self.advance().value
        if not self.eat_op("("):
            self.error('بعد از اسم تابع، پرانتز لازمه — مثال: تابع جمع(الف، ب)')
        params = []
        if not self.at_op(")"):
            while True:
                pt = self.peek()
                if pt.type != "NAME" or self.kw(pt) in RESERVED:
                    self.error("اسم پارامتر باید یه اسم فارسی باشه")
                pname = self.advance().value
                if pname in params:
                    self.error('پارامتر "{}" تکراریه'.format(pname), pt)
                params.append(pname)
                if self.eat_op(","):
                    continue
                break
        if not self.eat_op(")"):
            self.error("پرانتز تابع بسته نشده")
        self._allow_colon()
        body = self._block(tok.line)
        return FuncDef(name, params, body, tok.line)

    def return_statement(self):
        tok = self.advance()  # برگردان
        t = self.peek()
        if t.type == "NEWLINE" or t.type == "EOF":
            self._end_of_line()
            return Return(None, tok.line)
        value = self.expression()
        self._end_of_line()
        return Return(value, tok.line)

    # ─── عبارت‌ها (اولویت‌دار) ───

    def expression(self):
        return self._or()

    def _or(self):
        left = self._and()
        while self.at_kw("یا"):
            tok = self.advance()
            right = self._and()
            left = Bin("یا", left, right, tok.line)
        return left

    def _and(self):
        left = self._not()
        while self.at_kw("و"):
            tok = self.advance()
            right = self._not()
            left = Bin("و", left, right, tok.line)
        return left

    def _not(self):
        if self.at_kw("نه"):
            tok = self.advance()
            return Un("نه", self._not(), tok.line)
        return self._comparison()

    def _comparison(self):
        left = self._additive()
        while True:
            t = self.peek()
            op = None
            if t.type == "OP" and t.value in ("==", "!=", "<", "<=", ">", ">="):
                op = t.value
                self.advance()
            else:
                k = self.kw(t)
                if k in CMP_OPS and k not in ("==", "!=", "<", "<=", ">", ">="):
                    op = CMP_OPS[k]
                    self.advance()
                elif k in ("برابر", "نابرابر", "بزرگتر از", "کوچکتر از",
                           "بزرگتر مساوی", "کوچکتر مساوی"):
                    op = CMP_OPS[k]
                    self.advance()
            if op is None:
                return left
            right = self._additive()
            left = Bin(op, left, right, t.line)

    def _additive(self):
        left = self._multiplicative()
        while True:
            t = self.peek()
            if t.type == "OP" and t.value in ("+", "-"):
                self.advance()
                right = self._multiplicative()
                left = Bin(t.value, left, right, t.line)
            else:
                return left

    def _multiplicative(self):
        left = self._unary()
        while True:
            t = self.peek()
            op = None
            if t.type == "OP" and t.value in ("*", "/", "%"):
                op = t.value
                self.advance()
            else:
                k = self.kw(t)
                if k in ("ضربدر", "تقسیم بر", "باقیمانده"):
                    op = MUL_OPS[k]
                    self.advance()
            if op is None:
                return left
            right = self._unary()
            left = Bin(op, left, right, t.line)

    def _unary(self):
        t = self.peek()
        if t.type == "OP" and t.value == "-":
            self.advance()
            return Un("-", self._unary(), t.line)
        if self.at_kw("نه"):
            self.advance()
            return Un("نه", self._unary(), t.line)
        return self._postfix()

    def _postfix(self):
        node = self._primary()
        while True:
            if self.at_op("("):
                tok = self.advance()
                if not isinstance(node, Name):
                    self.error("اینجا فقط فراخوانی تابع با اسم مستقیم ممکنه", tok)
                args = self._args()
                node = Call(node, args, tok.line)
            elif self.at_op("["):
                tok = self.advance()
                idx = self.expression()
                if not self.eat_op("]"):
                    self.error("براکت بسته نشده")
                node = Index(node, idx, tok.line)
            else:
                return node

    def _args(self):
        args = []
        if self.at_op(")"):
            self.advance()
            return args
        while True:
            args.append(self.expression())
            if self.eat_op(","):
                if self.at_op(")"):
                    self.advance()
                    return args
                continue
            if self.eat_op(")"):
                return args
            self.error("پرانتز فراخوانی درست بسته نشده — پرانتز یا ویرگول جا مونده")

    def _primary(self):
        t = self.peek()
        if t.type == "NUM":
            self.advance()
            return Num(t.value)
        if t.type == "STR":
            self.advance()
            return Str(t.value)
        if t.type == "OP" and t.value == "(":
            self.advance()
            e = self.expression()
            if not self.eat_op(")"):
                self.error("پرانتز بسته نشده")
            return e
        if t.type == "OP" and t.value == "[":
            tok = self.advance()
            items = []
            if not self.at_op("]"):
                while True:
                    items.append(self.expression())
                    if self.eat_op(","):
                        if self.at_op("]"):
                            break
                        continue
                    break
            if not self.eat_op("]"):
                self.error("براکت لیست بسته نشده")
            return ListLit(items, tok.line)
        if t.type == "NAME":
            k = self.kw(t)
            if k in CONSTANTS:
                self.advance()
                return Const(CONSTANTS[k])
            if k in RESERVED:
                self.error('«{}» کلمه‌ی رزروشده‌ست و نمی‌تونه اسم باشه'.format(t.value))
            self.advance()
            return Name(t.value, t.line)
        if t.type == "EOF":
            raise IncompleteInput("عبارت ناتمام مونده", t.line)
        self.error("اینجا یه عبارت انتظار می‌رفت")
