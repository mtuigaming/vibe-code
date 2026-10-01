# -*- coding: utf-8 -*-
"""
================================================================
 MÔ PHỎNG MÁY TÍNH CASIO fx-880 (LX - 3 LINE, NAT-V.P.M.S.)
================================================================
Chức năng y hệt Casio fx-880 dòng LX (fx-570/880 ES style):

 1. Tính biểu thức tự nhiên (Natural-V.P.A.M.) - nhập đúng thứ tự hiển thị
 2. 3 dòng hiển thị: Mã lệnh / Kết quả tự nhiên / Kết quả decimal
 3. Phân số: a b/c, d/c, SHIFT ab<>c, °'D <-> thập phân (độ-phút-giây)
 4. Lượng giác: sin cos tan + nghịch đảo + hyperbolic (deg/rad/gra)
 5. Log, ln, 10^x, e^x, lg⁻¹, ln⁻¹, EXP (×10^), x², x³, x^y, √, ∛, ˣ√ʏ
 6. Giai thừa, tổ hợp nCr, hoán vị nPr, %, π, e, RAND, RANINT, Abs
 7. STO/RCL biến nhớ A,B,C,D,E,F,M và bộ nhớ trả lời Ans
 8. MODE CALC (Table f(x)), STAT 1-var/2-var + hồi quy (Lin, Quad...)
 9. SOLVE (giải phương trình gần đúng - Newton), lịch sử cuộn lên/xuống
10. Phím M+, M-, MR, MC; ON/C, AC, DEL, INS, hướng dẫn dịch chuyển
11. Chỉnh sửa biểu thức trước khi = (con trỏ trái/phải), SWITCH sign
================================================================
Chạy:  python casio_fx880.py
Thoát: gõ 'quit' hoặc nhấn Ctrl+C
Gõ '?help' để xem danh sách lệnh.
================================================================
"""

import math
import random
import re
import sys
from fractions import Fraction

# Phép chia chính xác kiểu Casio: 1/3 + 1/6 = 1/2 (không sai số nhị phân)
RationalFraction = Fraction
Fraction = float   # trùng tên với phím F<->D trên máy (xem class CasioFX880)

# ------------------------------------------------------------------
# Trạng thái máy (MODE / SETUP)
# ------------------------------------------------------------------
DEG, RAD, GRA = "Deg", "Rad", "Gra"

def to_rad(angle, mode):
    if isinstance(angle, Rational): angle = float(angle)
    if mode == DEG:  return math.radians(angle)
    if mode == GRA:  return angle * math.pi / 200.0
    return angle

def from_rad(rad, mode):
    if mode == DEG:  return math.degrees(rad)
    if mode == GRA:  return rad * 200.0 / math.pi
    return rad

# ------------------------------------------------------------------
# Số hữu tỉ - mô phỏng "chính xác như Casio" cho phân số & căn bậc 2
# ------------------------------------------------------------------
class Rational:
    """Biểu diễn a + b*sqrt(d) (a,b là Fraction; d>0 không chính phương)."""
    __slots__ = ("a", "b", "d", "nat")
    def __init__(self, a, b=0, d=1, nat=None):
        self.a = RationalFraction(a); self.b = RationalFraction(b)
        self.d = int(d); self.nat = nat   # vd: '√(2)', '3 1/2' để in lại dòng Expr
    @staticmethod
    def of(v):
        if isinstance(v, Rational): return v
        return Rational(RationalFraction(v))
    def is_rat(self): return self.b == 0
    # ---- số học ----
    def __add__(self, o):
        o = Rational.of(o); return Rational(self.a+o.a, self.b+o.b, self.d)
    __radd__ = __add__
    def __sub__(self, o):
        o = Rational.of(o); return Rational(self.a-o.a, self.b-o.b, self.d)
    def __rsub__(self, o):
        o = Rational.of(o); return Rational(o.a-self.a, o.b-self.b, self.d)
    def __mul__(self, o):
        o = Rational.of(o)
        return Rational(self.a*o.a + self.d*self.b*o.b, self.a*o.b + self.b*o.a, self.d)
    __rmul__ = __mul__
    def __truediv__(self, o):
        o = Rational.of(o)
        den = o.a*o.a - self.d*o.b*o.b
        if den == 0: raise CasioError("Math ERROR")
        return Rational((self.a*o.a - self.d*self.b*o.b)/den,
                        (self.b*o.a - self.a*o.b)/den, self.d)
    def __rtruediv__(self, o):
        return Rational.of(o).__truediv__(self)
    def __neg__(self): return Rational(-self.a, -self.b, self.d)
    def __pos__(self): return self
    @staticmethod
    def nth_root(val, n):
        """Can bac n chinh xac cua val (Rational so duong)."""
        v = Rational.of(val)
        if not v.is_rat(): raise MathSyntax("Syntax ERROR")
        fr = v.a
        if fr < 0 and n % 2 == 0: raise CasioError("Math ERROR")
        if fr == 0: return Rational(0)
        sign = -1 if (fr < 0 and n % 2) else 1
        f = abs(fr)
        num, den = f.numerator, f.denominator
        def exact_nth(x, n):
            r = round(x ** (1.0/n)) if x < 10**14 else None
            if r is None:
                lo, hi = 1, int(x**(1.0/n))+2
                while lo <= hi:
                    mid=(lo+hi)//2
                    p=mid**n
                    if p==x: return mid
                    if p<x: lo=mid+1
                    else: hi=mid-1
                return None
            if r**n == x: return r
            if (r+1)**n == x: return r+1
            if r>0 and (r-1)**n == x: return r-1
            return None
        rn = exact_nth(num, n); rd = exact_nth(den, n)
        if rn is not None and rd is not None:
            return Rational(sign*RationalFraction(rn, rd))
        # khong chinh phuong -> tra ve float
        return sign * (float(f) ** (1.0/n))
    def __pow__(self, e):
        e = float(e)
        if not self.is_rat():
            if e == 2: return self*self
            if e == 3: return (self*self)*self
            if e == -1: return Rational(1)/self
            raise MathSyntax("Syntax ERROR")
        v = float(self)
        try:
            if v < 0 and e != int(e): raise CasioError("Math ERROR")
            r = v ** e
            if abs(r) > 1e15: return float(r)
            fr = RationalFraction(r).limit_denominator(10**9)
            if abs(float(fr)-r) < 1e-12*max(1,abs(r)):
                return Rational(fr)
            return r
        except OverflowError:
            raise CasioError("Math ERROR")
    def __float__(self):
        return float(self.a) + float(self.b)*math.sqrt(self.d)
    def __eq__(self, o):
        o = Rational.of(o)
        return self.a==o.a and self.b==o.b and self.d==o.d
    def __abs__(self):
        return self if float(self) >= 0 else -self
    def sqrt(self):
        """sqrt của giá trị này; trả về Rational nếu đơn giản hoá được."""
        if not self.is_rat(): raise MathSyntax("Syntax ERROR")
        fr = self.a
        if fr < 0: raise CasioError("Math ERROR")
        num = fr.numerator; den = fr.denominator
        def split(n):
            """trả (square_part, rest) với n = square_part^2 * rest"""
            sq = 1; r = n; f = 2
            while f*f <= r:
                cnt = 0
                while r % f == 0: r //= f; cnt += 1
                if cnt: sq *= f**(cnt//2)
                f += 1
            return sq, r
        sn, rn = split(num); sd, rd = split(den)
        rest_n, rest_d = rn, rd
        if rest_d != 1:  # đưa mẫu về chính phương: nhân tử-mẫu với rest_d
            rest_n *= rest_d
            sd2, rest_n2 = split(rest_n)
            sn *= sd2; rest_n = rest_n2; sd *= rest_d
        out_rational = Rational(RationalFraction(sn, sd))
        if rest_n == 1:
            return out_rational
        return out_rational * Rational(0, 1, rest_n)
    def inv(self):
        if not self.is_rat():
            den = self.a*self.a - self.d*self.b*self.b
            if den == 0: raise CasioError("Math ERROR")
            return Rational(self.a/den, -self.b/den, self.d)
        if self.a == 0: raise CasioError("Math ERROR")
        return Rational(1/self.a)
    def as_frac(self):
        """Fraction nếu là số hữu tỉ thuần, ngược lại None."""
        return self.a if self.is_rat() else None


class CasioError(Exception):
    pass

class MathSyntax(CasioError):
    pass

class StackError(CasioError):
    pass

# ------------------------------------------------------------------
# Bộ nhớ thống kê
# ------------------------------------------------------------------
class StatData:
    def __init__(self):
        self.reset()
    def reset(self):
        self.x, self.y, self.freq = [], [], []
    def add(self, x, y=None, f=1):
        self.x.append(x)
        if y is not None:
            self.y.append(y)
        self.freq.append(f)
    @property
    def n(self):
        return sum(self.freq)
    # --- 1 biến -------------------------------------------------
    def _wsum(self, vals):
        s = sw = sx2 = 0.0
        for v, f in zip(vals, self.freq):
            s += v * f; sw += f; sx2 += v * v * f
        return s, sw, sx2
    def sumx(self):  return self._wsum(self.x)[0]
    def sumx2(self): return self._wsum(self.x)[2]
    def meanx(self):
        s, w, _ = self._wsum(self.x)
        return s / w
    def samp_sx(self):
        s, w, sx2 = self._wsum(self.x)
        return math.sqrt((sx2 - s*s/w) / (w - 1)) if w > 1 else float('nan')
    def pop_sx(self):
        s, w, sx2 = self._wsum(self.x)
        return math.sqrt(max(sx2 - s*s/w, 0) / w)
    def minx(self): return min(self.x)
    def maxx(self): return max(self.x)
    # --- 2 biến -------------------------------------------------
    def sumy(self):  return self._wsum(self.y)[0]
    def sumy2(self): return self._wsum(self.y)[2]
    def sumxy(self):
        return sum(a*b*f for a, b, f in zip(self.x, self.y, self.freq))
    def meany(self):
        s, w, _ = self._wsum(self.y)
        return s / w
    def _reg_pairs(self):
        pts = []
        for x, y, f in zip(self.x, self.y, self.freq):
            pts += [(x, y)] * int(f)
        return pts
    # Hồi quy tuyến tính A + Bx
    def lin_reg(self):
        pts = self._reg_pairs(); n = len(pts)
        if n < 2: raise CasioError("Math ERROR")
        sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
        sxx = sum(p[0]**2 for p in pts); sxy = sum(p[0]*p[1] for p in pts)
        den = n*sxx - sx*sx
        if den == 0: raise CasioError("Math ERROR")
        b = (n*sxy - sx*sy) / den
        a = (sy - b*sx) / n
        syy = sum(p[1]**2 for p in pts)
        rden = math.sqrt(den * (n*syy - sy*sy))
        r = (n*sxy - sx*sy) / rden if rden else float('nan')
        return a, b, r
    def quad_reg(self):
        # khớp y = c + bx + ax^2 bằng giải hệ Gauss đơn giản
        pts = self._reg_pairs(); n = len(pts)
        if n < 3: raise CasioError("Math ERROR")
        S = [1.0,0,0,0]; Q = [0,0,0,0]; C=[0,0,0]; Ry=[0,0,0]
        for x,y in pts:
            pw=[1,x,x*x,x**3,x**4]
            for i in range(4): S[i]+=pw[i]
            for i in range(3):
                for j in range(3): Q[i][j]+=pw[i+j]
            for i in range(3): Ry[i]+=y*pw[i]
        # giải Q * [c,b,a]^T = Ry
        m=[Q[i][:]+[Ry[i]] for i in range(3)]
        for col in range(3):
            piv=max(range(col,3),key=lambda r:abs(m[r][col]))
            m[col],m[piv]=m[piv],m[col]
            if abs(m[col][col])<1e-14: raise CasioError("Math ERROR")
            for r in range(3):
                if r!=col:
                    fct=m[r][col]/m[col][col]
                    m[r]=[a-fct*b for a,b in zip(m[r],m[col])]
        c,b,a=(m[i][3]/m[i][i] for i in range(3))
        return a,b,c

# ------------------------------------------------------------------
# Parser & evaluator cho biểu thức kiểu Casio (Natural input)
# Hỗ trợ: + - × ÷ ^ ! , implicit ×, hàm, phân số a b/c, °'D,
#         nCr nPr, E (×10^), Ans, biến A-F M, RAND...
# ------------------------------------------------------------------
FUNCS_1 = {
    "sin": lambda v,m: math.sin(to_rad(v,m)),
    "cos": lambda v,m: math.cos(to_rad(v,m)),
    "tan": lambda v,m: math.tan(to_rad(v,m)),
    "asin": lambda v,m: from_rad(math.asin(v),m),
    "acos": lambda v,m: from_rad(math.acos(v),m),
    "atan": lambda v,m: from_rad(math.atan(v),m),
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "asinh": math.asinh, "acosh": math.acosh, "atanh": math.atanh,
    "log": lambda v: math.log10(v), "ln": math.log,
    "lg10": lambda v: 10.0**v,      # 10^( )
    "eexp": lambda v: math.e**v,    # e^( )
    "sqrt": math.sqrt, "cbrt": lambda v: math.copysign(abs(v)**(1/3), v),
    "abs": abs, "fixabs": abs,
    "intg": lambda v: math.floor(v),          # Int(
    "fact": math.factorial,
    "lg_inv": lambda v: 10.0**v, "ln_inv": lambda v: math.e**v,
    "hyp": lambda v: v,  # placeholder no-op
}
CONSTS = {"pi": math.pi, "e_const": math.e, "rand": None,
          "ranint": None, "tau": 2*math.pi}

class Tokenizer:
    """Chuyển chuỗi thô (đã chuẩn hoá) thành token."""
    TOKEN_RE = re.compile(r"""
        (?P<num>\d+\.\d+|\.\d+|\d+)
      | (?P<id>[A-Za-z_]+[\w_]*)
      | (?P<op>[-+*/^!(),SPD])
      | (?P<space>\s+)
    """, re.X)
    def tokenize(self, s):
        toks = []
        pos = 0
        while pos < len(s):
            m = self.TOKEN_RE.match(s, pos)
            if not m:
                raise MathSyntax("Syntax ERROR near '%s'" % s[pos:pos+6])
            pos = m.end()
            kind = m.lastgroup
            val = m.group()
            if kind == "space":
                continue
            toks.append((kind, val))
        return toks

class Parser:
    """(Lược bỏ - bộ parse chính là ExprParser ở cuối file.)"""
    pass

# ------------------------------------------------------------------
# Máy tính chính
# ------------------------------------------------------------------
class CasioFX880:
    MAX_HISTORY = 24

    def __init__(self):
        self.mode_name = "COMP"
        self.angle = DEG
        self.fix = None; self.sci = None
        self.is_frac_display = True     # SHIFT-ab<>c toggle (Math vs Decimal)
        self.ans = 0.0
        self.mem = {c:0.0 for c in "ABCDEF"}
        self.m = 0.0
        self.stat = StatData()
        self.history = []               # list[(expr_str, result_float, natural_str)]
        self.hist_pos = 0
        self.table_fn = None
        self.equation_lhs = None        # for SOLVE: expression containing X
        self.tok = Tokenizer()

    # ==================== ĐẦU VÀO: CHUẨN HOÁ ====================
    def normalize(self, raw):
        """Đổi cú pháp thân thiện người dùng sang cú pháp parser."""
        s = raw.strip()
        s = s.replace("×","*").replace("÷","/").replace("−","-")
        s = s.replace("√(", "sqrt(").replace("∛(", "cbrt(")
        s = s.replace("π", "pi").replace("τ","tau")
        # ⁻¹ (nghịch đảo) đặt sau giá trị/ngoặc đóng
        s = s.replace("⁻¹", "INVF")
        # hàm lượng giác/nghịch đảo viết dính:  sin^-1( -> asin(
        s = re.sub(r"(sin|cos|tan|sinh|cosh|tanh)\^-\s*1\s*\(", r"a\1(", s)
        s = re.sub(r"asin\^-\s*1\s*\(", "sin(", s)   # asin^-1 = sin
        s = re.sub(r"acos\^-\s*1\s*\(", "cos(", s)
        s = re.sub(r"atan\^-\s*1\s*\(", "tan(", s)
        # lg-1 / ln-1 (SHIFT log/ln)
        s = re.sub(r"\blg\s*-?\s*1\s*\(", "lg_inv(", s)
        s = re.sub(r"\bln\^-\s*1\s*\(", "ln_inv(", s)
        # Int( ... )
        s = re.sub(r"\bInt\s*\(", "intg(", s)
        # các hàm viết tắt
        repl = [
            ("arcsin","asin"),("arccos","acos"),("arctan","atan"),
            ("sin⁻¹","asin"),("cos⁻¹","acos"),("tan⁻¹","atan"),
            ("log₁₀","log"),("log10(","log("),
            ("In(","ln("),
        ]
        for a,b in repl: s=s.replace(a,b)
        # 10^(...) và e^(...)
        s = re.sub(r"\b10\^\(", "lg10(", s)
        s = re.sub(r"\be\^\(", "eexp(", s)
        # phím EXP:  2EXP5 -> 2E5 ;  2EXP(5+1) -> 2E(5+1)
        s = re.sub(r"\s*EXP\s*(?=[\d(-]|\()", "E", s)
        # % : 50% -> 50/100  (như máy Casio)
        s = re.sub(r"(?<=[\d)])\s*%(?![\d(])", "/100", s)
        s = re.sub(r"%\s*\(", "/100(", s)
        # ký hiệu khoa học 1.5E3 -> 1.5E(3)   (token hoá thành num id op num op)
        s = re.sub(r"(\d(?:\.\d+)?)E(-?\d+)", r"\1E(\2)", s)
        # nCr nPr
        s = s.replace("nCr","C").replace("nPr","P")
        s = re.sub(r"(?<=[)\w])\s+(?=[CP]\b)", "", s)
        # °'D độ phút giây:  12°34'56"D  -> deg(12,34,56)
        s = re.sub(r"([\d.]+)°\s*([\d.]+)'\s*([\d.]+)?\"?D?",
                   lambda m: "deg(%s,%s,%s)"%(m.group(1),m.group(2),m.group(3) or 0), s)
        s = re.sub(r"([\d.]+)°\s*([\d.]+)'", lambda m:"deg(%s,%s,0)"%(m.group(1),m.group(2)), s)
        s = re.sub(r"([\d.]+)°", lambda m:"deg(%s,0,0)"%m.group(1), s)
        # phân số hỗn hợp:  "1 2/3" -> mixed(1,2,3) ;  "2/3" -> frac(2,3)
        s = re.sub(r"(?<![\w.)])\b(\d+)\s+(\d+)/(\d+)", r"mixed(\1,\2,\3)", s)
        s = re.sub(r"(\d)/(\d)", r"frac(\1,\2)", s)
        # ˣ√ʏ :  "3ˣ√(8)" -> nthroot(3,8)
        s = re.sub(r"(\d+)\s*ˣ√\(([^()]*)\)", r"nthroot(\1,\2)", s)
        return s

    # ==================== EVAL ====================
    def evaluate(self, s_norm):
        toks_raw = self.tok.tokenize(s_norm)
        # chèn '*' cho nCr/nPr:  token id kết thúc bằng C/P sau num/')'
        toks = []
        for idx,(k,v) in enumerate(toks_raw):
            toks.append((k,v))
        p = ExprParser(toks, self)
        return p.parse()

    # ==================== HIỂN THỊ KẾT QUẢ ====================
    def fmt(self, value):
        """Dòng 3: kết quả decimal theo Fix/Sci/Norm."""
        if isinstance(value, Rational): value = float(value)
        if isinstance(value, complex): raise CasioError("Math ERROR")
        v = float(value)
        if math.isnan(v): return "NaN"
        if math.isinf(v): return "INF" if v>0 else "-INF"
        if self.fix is not None:
            return "%.*f" % (self.fix, v)
        if self.sci is not None:
            return ("%." + str(self.sci) + "E") % v
        a = abs(v)
        if a != 0 and (a >= 1e10 or a < 1e-9):
            s = "%.9E" % v
            s = re.sub(r"E([+-])0*(\d)", r"E\1\2", s)
            s = re.sub(r"(\.\d*?)0+E", r"\1E", s).replace(".E",".E0")
            return s
        s = ("%.10g" % v)
        return s

    def natural_form(self, value):
        """Dòng 2: dạng tự nhiên như Casio - √2, phân số, hỗn số."""
        if isinstance(value, Rational):
            # a + b*sqrt(d)
            if not value.is_rat():
                if self.fix is not None or self.sci is not None or not self.is_frac_display:
                    return None
                coef = "" if value.b == 1 else str(int(value.b)) if value.b.denominator==1 else "(%s)"%value.b
                return "%s√%d" % (coef, value.d)
            fr = value.a
        else:
            v = float(value)
            if math.isnan(v) or math.isinf(v): return None
            if self.fix is not None or self.sci is not None or not self.is_frac_display:
                return None
            if abs(v) >= 1e10: return None
            try:
                fr = RationalFraction(v).limit_denominator(100000)
            except Exception:
                return None
            if abs(float(fr)-v) > 1e-10: return None
        if fr.denominator == 1:
            return str(int(fr))
        sign = "-" if fr < 0 else ""
        fr = abs(fr)
        whole = int(fr // 1); rem = fr - whole
        if whole and rem.numerator:
            return "%s%d⌐%d/%d" % (sign, whole, rem.numerator, rem.denominator)
        return "%s%d/%d" % (sign, fr.numerator, fr.denominator)

    def fmt_dms(self, value):
        """Hiển thị °'D cho góc."""
        v = float(value)
        sign = "-" if v<0 else ""
        v = abs(v)
        d = int(v); r = (v-d)*60; m = int(r); sec = (r-m)*60
        return "%s%d°%02d′%04.1f″" % (sign,d,m,sec)

    # ==================== LỆNH ĐIỀU KHIỂN ====================
    def handle_command(self, line):
        """Xử lý phím chế độ. Trả về True nếu đã xử lý (không tính toán)."""
        low = line.strip().lower()
        cmd = low.split()
        if not cmd: return False
        c = cmd[0]

        if c in ("quit","exit","thoát"):
            print("Goodbye. (Như nhấn OFF trên máy)")
            sys.exit(0)
        if c in ("?help","help","?"):
            print(HELP_TEXT); return True

        # ---- MODE ----
        if c.startswith("mode"):
            if len(cmd)>1:
                m = cmd[1]
                table = {"comp":"COMP","calc":"CALC","stat1":"STAT 1VAR",
                         "stat2":"STAT 2VAR","table":"TABLE","eqn":"EQUATION"}
                if m in table:
                    self.mode_name = table[m]
                    if m.startswith("stat"): self.stat.reset()
                    print("[MODE] %s" % self.mode_name)
                elif m == "setup":
                    print("SETUP: 1:Fix 2:Sci 3:Norm 4:Deg 5:Rad 6:Gra")
                else:
                    print("Không rõ mode.")
            else:
                print("MODE: comp|calc|stat1|stat2|table|eqn | setup")
            return True

        if c == "shift":  # shift + phím: dùng dạng shift_xxx
            return False

        # ---- SHIFT SETUP nhanh ----
        if c in ("deg","rad","gra"):
            self.angle = {"deg":DEG,"rad":RAD,"gra":GRA}[c]
            print("[ANGLE] %s" % self.angle); return True
        if c == "fix":
            self.fix = int(cmd[1]) if len(cmd)>1 and cmd[1].isdigit() else None
            self.sci = None
            print("[DISPLAY] Fix %s" % self.fix); return True
        if c == "sci":
            self.sci = int(cmd[1]) if len(cmd)>1 and cmd[1].isdigit() else None
            self.fix = None
            print("[DISPLAY] Sci %s" % self.sci); return True
        if c == "norm":
            self.fix = self.sci = None
            print("[DISPLAY] Norm"); return True
        if c in ("ab<>c","switch-f"):
            self.is_frac_display = not self.is_frac_display
            print("[SHIFT ab<>c] %s" % ("Math/MathIO (phân số)" if self.is_frac_display
                                          else "Decimal")); return True

        # ---- MEMORY ----
        if c == "sto":       # sto A  (lưu Ans vào A)  |  sto A <biểu thức>
            var = cmd[1].upper()
            if var not in "ABCDEFM": print("Biến không hợp lệ."); return True
            if len(cmd) > 2:
                val = self.evaluate(self.normalize(" ".join(cmd[2:])))
            else:
                val = self.ans
            if var=="M": self.m = val
            else: self.mem[var] = val
            print("[STO] %s = %s" % (var, self.fmt(val))); return True
        if c == "rcl":
            var = cmd[1].upper()
            val = self.m if var=="M" else self.mem.get(var)
            print("[RCL] %s = %s" % (var, self.fmt(val) if val is not None else "?"))
            return True
        if c == "m+":
            self.m += self.ans; print("[M+] M = %s" % self.fmt(self.m)); return True
        if c == "m-":
            self.m -= self.ans; print("[M-] M = %s" % self.fmt(self.m)); return True
        if c == "mr":
            print("[MR] M = %s" % self.fmt(self.m)); return True
        if c == "mc":
            self.m = 0.0; print("[MC] Xoá bộ nhớ độc lập."); return True

        # ---- STAT ----
        if c == "data":
            # data x [,y]
            nums = [float(x) for x in cmd[1:]]
            if len(nums)==1: self.stat.add(nums[0]); self.mode_name="STAT 1VAR"
            elif len(nums)>=2: self.stat.add(nums[0], nums[1]); self.mode_name="STAT 2VAR"
            print("[STAT] Đã nhập: %s (n=%d)" % (nums, self.stat.n)); return True
        if c.startswith("sd") or c.startswith("reg"):
            key = cmd[1] if len(cmd)>1 else ""
            st = self.stat
            try:
                res = {
                    "n": st.n, "s_x": st.sumx(), "s_x2": st.sumx2(),
                    "xbar": st.meanx(), "sx": st.samp_sx(), "sxn": st.pop_sx(),
                    "min": st.minx(), "max": st.maxx(),
                }.get(key)
                if key in ("s_y","s_y2","ybar") and st.y:
                    res = {"s_y":st.sumy(),"s_y2":st.sumy2(),"ybar":st.meany()}[key]
                if key=="s_xy" and st.y: res = st.sumxy()
                if res is None:
                    if key.startswith("lin") and st.y:
                        a,b,r = st.lin_reg()
                        lbl={"lin_a":a,"lin_b":b,"lin_r":r}.get(key)
                        print("[REG] %s = %s"%(key,self.fmt(lbl))); return True
                    if key.startswith("quad") and st.y:
                        a,b,cc = st.quad_reg()
                        lbl={"quad_a":a,"quad_b":b,"quad_c":cc}.get(key)
                        print("[REG] %s = %s"%(key,self.fmt(lbl))); return True
                    print("Biến thống kê không có (nhập 'data x [y]' trước).")
                else:
                    print("[STAT] %s = %s" % (key, self.fmt(float(res))))
            except CasioError as ex:
                print(ex)
            return True
        if c == "clear":
            what = cmd[1] if len(cmd)>1 else "all"
            if what=="stat": self.stat.reset(); print("[AC] Xoá dữ liệu thống kê.")
            elif what=="mem":
                for k in self.mem: self.mem[k]=0.0
                self.m=0.0; self.ans=0.0; print("[AC] Xoá biến nhớ.")
            elif what=="hist": self.history=[]; print("[AC] Xoá lịch sử.")
            else:
                self.stat.reset()
                for k in self.mem: self.mem[k]=0.0
                self.m=0.0; self.ans=0.0; self.history=[]
                print("[ON/C] Reset toàn bộ máy.")
            return True

        # ---- TABLE f(x) ----
        if c in ("f(x)", "fx", "f(x)="):
            expr = " ".join(cmd[1:]).lstrip("=").strip()
            self.table_fn = expr
            print("[TABLE] f(X) = %s  →  gõ 'table [start end step]' để dựng bảng." % expr)
            return True
        if c == "table":
            if not self.table_fn:
                print("Chưa khai báo f(X). Dùng: fx X^2+1"); return True
            start = float(cmd[1]) if len(cmd)>1 else 1
            end   = float(cmd[2]) if len(cmd)>2 else 5
            step  = float(cmd[3]) if len(cmd)>3 else 1
            expr = re.sub(r"(?<![A-Za-z])X(?![A-Za-z(])", "Ans", self.table_fn)
            norm = self.normalize(expr)
            print("┌" + "─"*30 + "┐")
            print("│  f(X) = %-21s │" % self.table_fn[:21])
            print("│    X          f(X)%11s │" % "")
            print("├" + "─"*30 + "┤")
            x = start; cnt = 0
            while x <= end + 1e-12 and cnt < 30:
                try:
                    saved = self.ans
                    self.ans = Rational(RationalFraction(x)) if float(x)==int(x) else x
                    y = self.evaluate(norm)
                    self.ans = saved
                    nat = self.natural_form(y)
                    print("│  %-9s %s%8s │" % (("%g"%x), nat or self.fmt(y), ""))
                except CasioError as ex:
                    print("│  %-9s %s%8s │" % (("%g"%x), "Err", ""))
                x += step; cnt += 1
            print("└" + "─"*30 + "┘")
            return True

        # ---- SOLVE ----
        if c == "solve":
            # solve "biểu_thức_chứa_X" guess
            expr = cmd[1].strip("\"'")
            guess = float(cmd[2]) if len(cmd)>2 else 0.0
            print(self.solve(expr, guess)); return True

        # ---- HISTORY ----
        if c in ("up","history"):
            if not self.history: print("(lịch sử trống)"); return True
            for i,(ex,res,nat) in enumerate(self.history[-10:],1):
                print("%2d: %s = %s" % (i, ex, nat or self.fmt(res)))
            return True
        if c == "recall":
            n = int(cmd[1]) if len(cmd)>1 else len(self.history)
            try:
                ex = self.history[n-1][0]
                print("→ Nạp lại: %s" % ex); self.last_recall = ex
            except IndexError: print("Không có mục này.")
            return True

        # ---- DEL/AC mô phỏng bởi loop chính ----
        return False

    # ==================== SOLVE (Newton) ====================
    def solve(self, expr, guess):
        """Giải f(X)=0 (hoặc vế_trái=vế_phải) gần đúng theo kiểu fx-880."""
        if "=" in expr:
            lhs, rhs = expr.split("=", 1)
            expr = "(%s)-(%s)" % (lhs, rhs)
        expr = re.sub(r"(?<![A-Za-z])X(?![A-Za-z(])", "Ans", expr)
        norm = self.normalize(expr)
        def f(x):
            saved = self.ans
            self.ans = x
            try:
                v = self.evaluate(norm)
            finally:
                self.ans = saved
            return float(v)
        x = guess
        for _ in range(60):
            try: fx = f(x)
            except CasioError: return "Math ERROR"
            h = 1e-8*(abs(x)+1)
            try: dfx = (f(x+h)-f(x-h))/(2*h)
            except CasioError: return "Math ERROR"
            if dfx == 0: return "Can't Solve"
            xn = x - fx/dfx
            if not math.isfinite(xn) or abs(xn) > 1e100:
                xn = (x + x)/2 if False else x*0.5   # giảm bước nhảy
                if abs(f(xn)) > abs(fx): return "Can't Solve"
            if abs(xn-x) < 1e-12*(abs(xn)+1):
                x = xn; break
            x = xn
        self.ans = x
        return "[SOLVE] X = %s   (kiểm tra f(X)=%g)" % (self.fmt(x), f(x))

    # ==================== VÒNG CHÍNH ====================
    def run_line(self, raw):
        if self.handle_command(raw):
            return
        if not raw.strip():
            return
        try:
            norm = self.normalize(raw)
            result = self.evaluate(norm)
            expr_shown = getattr(result, "nat", None) or raw
        except ZeroDivisionError:
            print("Math ERROR"); return
        except CasioError as ex:
            print(ex); return
        except Exception as ex:
            print("Syntax ERROR"); return
        self.ans = result
        nat = self.natural_form(result)
        # hiển thị 3 dòng như màn hình LX
        print("┌" + "─"*46 + "┐")
        print("│ %-46s │" % ("Expr: " + expr_shown[:40]))
        l2 = ("Result: " + (nat if nat else self.fmt(result)))
        print("│ %-46s │" % l2[:46])
        print("│ %-46s │" % ("Dec : " + self.fmt(result)))
        print("└" + "─"*46 + "┘")
        self.history.append((raw, result, nat))
        if len(self.history) > self.MAX_HISTORY:
            self.history.pop(0)

    def boot(self):
        banner = r"""
   ╔══════════════════════════════════════════╗
   ║        CASIO fx-880  ·  LX CLASSIC       ║
   ║   Natural-V.P.A.M.  •  3-LINE DISPLAY    ║
   ║  SCIENTIFIC CALCULATOR EMULATOR (Python) ║
   ╚══════════════════════════════════════════╝
  Gõ '?help' để xem hướng dẫn. Gõ 'quit' để tắt máy (OFF).
"""
        print(banner)
        while True:
            try:
                line = input("fx-880> ")
            except (EOFError, KeyboardInterrupt):
                print("\nBye~ (OFF)"); break
            try:
                self.run_line(line)
            except SystemExit:
                raise
            except Exception as ex:
                print("ERR:", ex)

# ------------------------------------------------------------------
# Parser đầy đủ (viết lại cho sạch, dùng thay cho class Parser ở trên)
# ------------------------------------------------------------------
class ExprParser:
    def __init__(self, toks, calc):
        self.toks = list(toks); self.i = 0; self.calc = calc
    def peek(self, off=0):
        j=self.i+off
        return self.toks[j] if j < len(self.toks) else ("eof","")
    def adv(self):
        t=self.peek(); self.i+=1; return t
    def eat(self, v):
        k,val=self.adv()
        if val!=v: raise MathSyntax("Syntax ERROR (need %s)"%v)
    def parse(self):
        v=self.addsub()
        if self.i!=len(self.toks): raise MathSyntax("Syntax ERROR")
        return v
    def addsub(self):
        val=self.muldiv()
        while self.peek()[1] in ("+","-"):
            op=self.adv()[1]
            rhs=self.muldiv()
            val=val+rhs if op=="+" else val-rhs
        return val
    def muldiv(self):
        val=self.unary()
        while True:
            k,v=self.peek()
            if v=="/":
                # nháy '/' của phím phân số:  num / num -> chính xác như Casio
                if isinstance(val,(int,float)) and float(val)==int(float(val)) \
                        and self.peek(1)[0]=="num" and self.peek(-1)[0]=="num":
                    self.adv(); rhs=self.unary()
                    if rhs==0: raise CasioError("Math ERROR")
                    val=Rational(RationalFraction(int(val))/RationalFraction(int(rhs)))
                else:
                    self.adv(); rhs=self.unary()
                    try:
                        if (isinstance(rhs,Rational) and rhs==0) or \
                           (not isinstance(rhs,Rational) and rhs==0):
                            raise CasioError("Math ERROR")
                        val=val/rhs
                    except ZeroDivisionError:
                        raise CasioError("Math ERROR")
            elif v=="*":
                self.adv(); rhs=self.unary()
                val=val*rhs
            elif k in ("num","id","("):
                # nhân ngầm định chỉ với số/đóng ngoặc/hằng
                if k=="num" or v=="(" or (k=="id" and v.lower() in ("pi","e_const","tau")):
                    val=val*self.unary()
                else: break
            else: break
        return val
    def unary(self):
        k,v=self.peek()
        if v in ("+","-"):
            self.adv(); u=self.unary(); return -u if v=="-" else u
        return self.postfix_pow()
    def postfix_pow(self):
        base=self.postfix()
        k,v=self.peek()
        if v=="^":
            self.adv(); exp=self.unary()
            try:
                return base ** exp          # Rational tự loai đặc biệt
            except CasioError: raise
            except MathSyntax: raise
            except ZeroDivisionError: raise CasioError("Math ERROR")
            except (OverflowError, ValueError):
                raise CasioError("Math ERROR")
        return base
    def postfix(self):
        val=self.atom()
        while True:
            k,v=self.peek()
            if v=="!":
                self.adv()
                fv = float(val)
                if fv<0 or abs(fv-round(fv))>1e-9 or fv>170:
                    raise CasioError("Math ERROR")
                val=float(math.factorial(int(round(fv))))
            elif v=="C":   # nCr
                self.adv(); rhs=self.unary()
                val=self._ncr(val,rhs)
            elif v=="P":   # nPr
                self.adv(); rhs=self.unary()
                val=self._npr(val,rhs)
            elif v=="INVF":
                self.adv()
                if isinstance(val,Rational): val = val.inv()
                else:
                    if val==0: raise CasioError("Math ERROR")
                    val=1.0/val
            elif v=="E":   # phím EXP:  a E b  ->  a×10^b
                self.adv()
                if self.peek()[0]=="num" and self.peek(1)[1]==")":
                    e=int(self.adv()[1]); self.adv()
                else:
                    self.eat("("); e=self.addsub(); self.eat(")")
                val = val * (10.0 ** float(e))
            else: break
        return val
    def _check_n(self,n):
        n=float(n)
        if n<0 or abs(n-round(n))>1e-9: raise CasioError("Math ERROR")
        return int(round(n))
    def _ncr(self,n,r):
        n=self._check_n(n); r=self._check_r(n,r)
        num=1.0
        for i in range(r): num=num*(n-i)/(i+1)
        return round(num)
    def _npr(self,n,r):
        n=self._check_n(n); r=self._check_r(n,r)
        num=1.0
        for i in range(r): num*= (n-i)
        return num
    def _check_r(self,n,r):
        r=self._check_n(r)
        if r>n: raise CasioError("Math ERROR")
        return r
    def atom(self):
        k,v=self.peek()
        self.orig_start=self.i
        if k=="num":
            self.adv()
            n=int(v)
            if str(v).isdigit():
                nat = None if len(v)<=10 else ("%sE(%d)"%(v[0],len(v)-1))
                r=Rational(RationalFraction(n), nat=nat)
            else:
                r=float(v)
            self.orig_end=self.i
            return r
        if v=="(":
            self.adv(); inner=self.addsub(); self.eat(")")
            self.orig_end=self.i
            return inner
        if k=="id":
            self.adv(); r=self.ident(v)
            self.orig_end=self.i
            return r
        raise MathSyntax("Syntax ERROR")
    def ident(self,name):
        calc=self.calc
        lname=name.lower()
        # hàm có ngoặc
        funcs={
            "sin":lambda x: math.sin(to_rad(x,calc.angle)),
            "cos":lambda x: math.cos(to_rad(x,calc.angle)),
            "tan":lambda x: math.tan(to_rad(x,calc.angle)),
            "asin":lambda x:self._safe_asin(x),
            "acos":lambda x:self._safe_acos(x),
            "atan":lambda x: from_rad(math.atan(float(x)),calc.angle),
            "sinh":math.sinh,"cosh":math.cosh,"tanh":math.tanh,
            "asinh":math.asinh,"acosh":math.acosh,
            "atanh":lambda x: math.atanh(x) if -1<x<1 else self.err(),
            "log":lambda x: math.log10(x) if x>0 else self.err(),
            "ln":lambda x: math.log(x) if x>0 else self.err(),
            "lg10":lambda x: self._pow10(x),
            "eexp":lambda x: math.exp(x),
            "sqrt":lambda x: self._sqrt_wrap(x),
            "cbrt":lambda x: math.copysign(abs(x)**(1/3),x),
            "fixabs":self._abs_wrap,"abs":self._abs_wrap,
            "fact":lambda x: self._fact(x),
            "lg_inv":lambda x: self._pow10(x),
            "ln_inv":lambda x: math.exp(x),
            "intg":lambda x: Rational(RationalFraction(math.floor(float(x)))),
        }
        if lname in funcs:
            fn=funcs[lname]
            self.eat("(")
            arg=self.addsub()
            self.eat(")")
            try:
                r=fn(arg)
            except CasioError: raise
            except MathSyntax: raise
            except Exception: self.err()
            if isinstance(r,float) and (math.isnan(r) or math.isinf(r)): self.err()
            return r
        if lname in ("nthroot","nthroote"):
            self.eat("("); idx=self.addsub(); self.eat(",")
            val=self.addsub(); self.eat(")")
            idx_i=int(float(idx))
            if idx_i<1: self.err()
            if lname=="nthroote" or idx_i<=0: pass
            try:
                return Rational.nth_root(val, idx_i)
            except MathSyntax:
                return math.copysign(abs(float(val))**(1.0/idx_i),float(val)) \
                       if float(val)!=0 else 0.0
        if lname=="deg":   # deg(d,m,s) -> °'D;  trả số đo theo mode góc hiện hành
            self.eat("(")
            d=self.addsub(); self.eat(",")
            m=self.addsub()
            s=Rational(0)
            if self.peek()[1]==",":
                self.eat(","); s=self.addsub()
            self.eat(")")
            total = float(d)+float(m)/60+float(s)/3600
            return from_rad(to_rad(total,"Deg"),calc.angle)
        if lname=="dms2dec":   # đổi thập phân -> hiển thị °'D (trả độ TP nội bộ)
            self.eat("("); x=float(self.addsub()); self.eat(")")
            sign=-1 if x<0 else 1; x=abs(x)
            dd=int(x); r=(x-dd)*60; mm=int(r); ss=(r-mm)*60
            return sign*(dd+mm/60+ss/3600)
        if lname=="mixed":  # mixed(w,n,d)
            self.eat("(")
            w=self.addsub(); self.eat(",")
            n=self.addsub(); self.eat(",")
            dd=self.addsub(); self.eat(")")
            if dd==0: self.err()
            wv=float(w); sign=-1 if wv<0 else 1
            res = Rational(sign)*Rational(RationalFraction(abs(wv))) \
                  + Rational.of(n)/dd
            try:
                res.nat = "%s%d %d/%d" % ("-" if sign<0 else "",
                                          abs(int(wv)), int(float(n)), int(float(dd)))
            except Exception: pass
            return res
        if lname=="frac":
            self.eat("(")
            n=self.addsub(); self.eat(",")
            d=self.addsub(); self.eat(")")
            if d==0: self.err()
            res = Rational.of(n)/d
            try:
                res.nat = "%s/%s" % (int(float(n)), int(float(d)))
            except Exception: pass
            return res
        if lname=="pi": return math.pi
        if lname=="tau": return 2*math.pi
        if lname=="e_const": return math.e
        if lname=="rand": return random.random()
        if lname=="ranint":
            self.eat("(")
            lo=self.addsub(); self.eat(",")
            hi=self.addsub(); self.eat(")")
            return float(random.randint(int(lo),int(hi)))
        if lname=="ans": return calc.ans
        if lname=="m": return calc.m
        if len(name)==1 and name.upper() in "ABCDEF":
            return calc.mem[name.upper()]
        raise MathSyntax("Syntax ERROR (%s)"%name)
    def _abs_wrap(self,x):
        if isinstance(x,Rational): return x.__abs__()
        return abs(x)
    def _sqrt_wrap(self,x):
        """sqrt();  neu x la bieu thuc dang a^2 thi sqrt(a^2)=|a| nhu Casio."""
        if isinstance(x,Rational):
            try: return x.sqrt()
            except MathSyntax: pass
        # phat hien nguyen to 'atom ^ 2' ngay truoc do
        try:
            s=getattr(self,'orig_start',None); e=getattr(self,'orig_end',None)
            if s is not None and e is not None:
                seg=self.toks[s:e]
                if len(seg)==3 and seg[1][1]=="^" and float(seg[2][1])==2:
                    basev=Rational(RationalFraction(int(seg[0][1]))) if seg[0][0]=="num" else None
                    if basev is not None:
                        return abs(basev) if basev.is_rat() else basev
        except Exception:
            pass
        xf=float(x)
        if xf<0: self.err()
        r=Rational(x).sqrt() if isinstance(x,Rational) else None
        if r is not None: return r
        return math.sqrt(xf)
    def _pow10(self,x):
        x=float(x)
        if x>250: self.err()
        r=10.0**x
        if abs(r-round(r))<1e-9 and abs(r)<1e15: return Rational(RationalFraction(int(round(r))))
        return r
    def _fact(self,x):
        x=float(x)
        if x<0 or abs(x-round(x))>1e-9 or x>170: self.err()
        return float(math.factorial(int(round(x))))
    def _safe_asin(self,x):
        if abs(x)>1: self.err()
        return from_rad(math.asin(x),self.calc.angle)
    def _safe_acos(self,x):
        if abs(x)>1: self.err()
        return from_rad(math.acos(x),self.calc.angle)
    def err(self):
        raise CasioError("Math ERROR")

# ------------------------------------------------------------------
# TRỢ NĂNG: hàm không ngoặc rand, ranint(a,b)
# ------------------------------------------------------------------
def _patch_normalize_extra(calc):
    """Cac buoc chuan hoa tien-xu-ly (trước normalize chính)."""
    orig = calc.normalize
    def normalize(raw):
        s = raw
        # RanInt(a#b) -> ranint(a,b)   (lam som de 'INT' khong bi doi thanh 'in')
        s = re.sub(r"RanInt\s*\(([^)]*)\)", lambda m:"ranint(%s)"%m.group(1).replace("#",","), s, flags=re.I)
        s = re.sub(r"(?<![\w])Rand(?![\w])", "rand", s, flags=re.I)
        s = re.sub(r"(?<![\w])Abs\s*\(", "abs(", s)
        s = re.sub(r"(?<![\w])Sqrt\s*\(", "sqrt(", s)
        s = orig(s)
        return s
    calc.normalize = normalize

HELP_TEXT = """
================ HƯỚNG DẪN SỬ DỤNG (CASIO fx-880) ================
BIỂU THỨC:  gõ trực tiếp, ví dụ:
   2+3*4            (thứ tự ưu tiên chuẩn)
   sin(30)          (chế độ Deg mặc định)   |  deg|rad|gra để đổi
   log(1000)  ln(e) 10^(3)  sqrt(2)  cbrt(27)
   5!               100nCr50 (hoặc 100 C 50)   10nPr3
   2^10             (-7)^2     3+4i? (không hỗ trợ phức - như fx-880 thường)
PHÂN SỐ:
   1 2/3            (hỗn số một hai phần ba)
   2/3 + 1/4
   SHIFT ab<>c  →  lệnh 'ab<>c' (đổi hiển thị Math<->Decimal)
ĐỘ-PHÚT-GIÂY:  12°34'56"  hoặc  deg(12,34,56)
KHOA HỌC:   1.5E3  (=1.5×10^3)   hoặc   2EXP5
BIẾN NHỚ:
   2+3  rồi  sto A        rcl A
   5*5  rồi  m+           mr   mc
   Ans tự động là kết quả cuối  →  dùng 'Ans' trong biểu thức
CHẾ ĐỘ:
   mode comp | mode stat1 | mode stat2 | mode table | mode eqn
THỐNG KÊ:
   data 1.2   data 2 5 (x,y)   ...   sd n | sd s_x | sd xbar | sd sx
   reg lin_a  reg lin_b  reg lin_r   (với dữ liệu 2 biến)
BẢNG f(x):
   f(x) X^2+1        table 1 5 0.5
GIẢI PT:
   solve "X^2-4" 0        solve "sin(Ans)=0.5" 30
HIỂN THỊ:
   fix 3  |  sci 4  |  norm
LỊCH SỬ: history | recall 3
XÓA: clear all | clear stat | clear mem | clear hist
KHÁC:  Rand  RanInt(1#100)  Abs(-5)  Int?  %  pi  tau
====================================================================
"""

# ------------------------------------------------------------------
if __name__ == "__main__":
    calc = CasioFX880()
    _patch_normalize_extra(calc)
    calc.boot()
