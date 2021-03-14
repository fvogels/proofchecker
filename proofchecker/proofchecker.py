import math
from fractions import Fraction


class ParseError(Exception):
    pass

def is_alpha(c):
    return 'A' <= c and c <= 'Z' or 'a' <= c and c <= 'z' or c == '_'

def is_digit(c):
    return '0' <= c and c <= '9'

operators = {'==', '<=', '<', '+', '-', '#', '(', ')', ',', '==>', ':'}
operatorPrefixes = set()
for operator in operators:
    for i in range(1,len(operator) + 1):
        operatorPrefixes.add(operator[:i])

keywords = ['assert', 'and', 'True', 'Herschrijven', 'met', 'in', 'Z', 'op', 'Wet']

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = -1
        self.line = 0
        self.startOfLine = 0
        self.eat()

    def get_token_value(self):
        return self.text[self.tokenStart:self.pos]

    def eat(self):
        if 0 <= self.pos and self.text[self.pos] == '\n':
            self.line += 1
            self.startOfLine = self.pos + 1
        self.pos += 1
        if self.pos == len(self.text):
            self.c = '\0'
        else:
            self.c = self.text[self.pos]

    def tokenLoc(self):
        return (self.line, self.tokenStart - self.startOfLine)

    def error(self, msg):
        raise ParseError("%d:%d: %s" % (self.line, self.pos - self.startOfLine, msg))

    def next_token(self):
        while self.c == ' ':
            if self.pos == self.startOfLine:
                self.error("Indentation is not supported")
            self.eat()
        self.tokenStart = self.pos
        if self.c == '\0':
            return 'EOF'
        if self.c == '\n':
            self.eat()
            self.startOfLine = self.pos
            return 'EOL'
        if is_alpha(self.c):
            self.eat()
            while is_alpha(self.c) or is_digit(self.c):
                self.eat()
            if self.get_token_value() in keywords:
                return self.get_token_value()
            return 'identifier'
        if is_digit(self.c):
            self.eat()
            while is_digit(self.c):
                self.eat()
            return 'number'
        operatorLength = 0
        operatorPrefixLength = 1
        while True:
            operatorPrefix = self.text[self.tokenStart:self.tokenStart + operatorPrefixLength]
            if not operatorPrefix in operatorPrefixes:
                break
            if operatorPrefix in operators:
                operatorLength = operatorPrefixLength
            operatorPrefixLength += 1
        if operatorLength == 0:
            self.error("Bad token")
        for i in range(operatorLength):
            self.eat()
        return self.get_token_value()

class Parser:
    def __init__(self, text):
        self.lexer = Lexer(text)
        self.tokenType = self.lexer.next_token()
        self.tokenLoc = self.lexer.tokenLoc()

    def error(self, msg):
        raise ParseError("%s: %s" % (self.tokenLoc, msg))

    def eat(self):
        value = self.lexer.get_token_value()
        self.tokenType = self.lexer.next_token()
        self.tokenLoc = self.lexer.tokenLoc()
        return value

    def parsePrimaryExpression(self):
        if self.tokenType == 'identifier':
            x = self.eat()
            if self.tokenType == '(':
                self.eat()
                args = []
                if self.tokenType != ')':
                    args.append(self.parseExpression())
                    while self.tokenType == ',':
                        self.eat()
                        args.append(self.parseExpression())
                self.expect(')')
                return 'call', x, tuple(args)
            return 'var', x
        elif self.tokenType == 'number':
            v = int(self.eat())
            return 'int', v
        elif self.tokenType == 'True':
            self.eat()
            return 'True',

    def parseAddition(self):
        e = self.parsePrimaryExpression()
        while True:
            if self.tokenType == '+':
                self.eat()
                e2 = self.parsePrimaryExpression()
                e = ('+', e, e2)
            elif self.tokenType == '-':
                self.eat()
                e2 = self.parsePrimaryExpression()
                e = ('-', e, e2)
            else:
                return e

    def parseComparison(self):
        e = self.parseAddition()
        if self.tokenType in ['==', '<=', '<']:
            operator = self.tokenType
            self.eat()
            e2 = self.parseAddition()
            result = (operator, e, e2)
            e = e2
            while self.tokenType in ['==', '<=', '<']:
                operator = self.tokenType
                self.eat()
                e2 = self.parseAddition()
                result = ('and', result, (operator, e, e2))
                e = e2
            return result
        else:
            return e

    def expect(self, tokenType):
        if self.tokenType != tokenType:
            self.parseError('%s expected, found %s' % (tokenType, self.tokenType))
        return self.eat()

    def parseConjunction(self):
        e = self.parseComparison()
        while self.tokenType == 'and':
            self.eat()
            e2 = self.parseConjunction()
            e = ('and', e, e2)
        return e

    def parseImplication(self):
        e = self.parseConjunction()
        if self.tokenType == '==>':
            self.eat()
            return ('==>', e, self.parseImplication())
        return e

    def parseExpression(self):
        return self.parseImplication()

    def parseProofLine(self):
        line, _ = self.tokenLoc
        self.expect('assert')
        e = self.parseConjunction()
        if self.tokenType == '#':
            self.eat()
            if self.tokenType == 'Herschrijven':
                self.eat()
                self.expect('met')
                i = int(self.expect('number'))
                self.expect('in')
                j = int(self.expect('number'))
                justification = ('Herschrijven', i, j)
            elif self.tokenType == 'Z':
                self.eat()
                i = None
                if self.tokenType == 'op':
                    self.eat()
                    i = int(self.expect('number'))
                justification = ('Z', i)
            elif self.tokenType == 'identifier':
                lawName = self.eat()
                self.expect('op')
                indices = [int(self.expect('number'))]
                while self.tokenType == ',':
                    self.eat()
                    indices.append(int(self.expect('number')))
                justification = ('law', lawName, tuple(indices))
            else:
                self.error('Justification keyword not supported')
        else:
            justification = None
        self.expect('EOL')
        return (line, e, justification)

    def parseProof(self):
        while self.tokenType == 'EOL':
            self.eat()
        lines = []
        while self.tokenType == 'assert':
            lines.append(self.parseProofLine())
        return lines

    def parseLaw(self):
        self.expect('#')
        self.expect('Wet')
        name = self.expect('identifier')
        self.expect(':')
        rule = self.parseImplication()
        self.expect('EOL')
        return (name, rule)

def get_rewrites(e, lhs, rhs):
    rewrites = [e] # e itself is a rewrite of itself
    if e == lhs:
        rewrites.append(rhs)
    if e == rhs:
        rewrites.append(lhs)
    if e[0] in ['==', '<=', '<', '+', '-']:
        for e1 in get_rewrites(e[1], lhs, rhs):
            for e2 in get_rewrites(e[2], lhs, rhs):
                rewrites.append((e[0], e1, e2))
    return rewrites

class ProofError(Exception):
    pass

def get_conjuncts(e):
    if e[0] == 'and':
        return get_conjuncts(e[1]) + get_conjuncts(e[2])
    else:
        return [e]

def add_polys(poly1, poly2):
    poly1Keys = set(poly1.keys())
    poly2Keys = set(poly2.keys())
    result = {}
    for key in poly1Keys - poly2Keys:
        result[key] = poly1[key]
    for key in poly2Keys - poly1Keys:
        result[key] = poly2[key]
    for key in poly1Keys & poly2Keys:
        value = poly1[key] + poly2[key]
        if value == 0:
            pass
        else:
            result[key] = value
    return result

def scale_poly(coef, poly):
    if coef == 0:
        return {}
    else:
        result = {}
        for key in poly.keys():
            result[key] = coef * poly[key]
        return result

def get_poly(e):
    if e[0] == 'var':
        return {(e,): 1}
    elif e[0] == 'int':
        if e[1] == 0:
            return {}
        else:
            return {(): e[1]}
    elif e[0] == '+':
        poly1 = get_poly(e[1])
        poly2 = get_poly(e[2])
        return add_polys(poly1, poly2)
    elif e[0] == '-':
        poly1 = get_poly(e[1])
        poly2 = get_poly(e[2])
        return add_polys(poly1, scale_poly(-1, poly2))
    else:
        raise ProofError("get_poly: not supported: " + str(e))

def is_tautology(e):
    if e[0] not in ['==', '<=', '<']:
        return False
    poly = get_poly(('-', e[2], e[1]))
    if e[0] == '==':
        return poly == {}
    elif e[0] == '<=':
        return set(poly.keys()) == set() or set(poly.keys()) == {()} and 0 <= poly[()]
    else:
        return set(poly.keys()) == {()} and 0 < poly[()]

def get_polyc(eq):
    poly = get_poly(('-', eq[2], eq[1]))
    c = Fraction(0)
    if () in poly:
        c = Fraction(poly[()])
        del poly[()]
    op = eq[0]
    if op == '<':
        c -= 1
        op = '<='
    if poly != {}:
        gcd = math.gcd(*poly.values())
        if op == '==' and poly[min(poly.keys())] < 0:
            gcd *= -1
        for key in list(poly.keys()):
            poly[key] /= gcd
        c /= gcd
    return op, c, poly

def follows_in_Z_from(consequent, antecedent):
    if not {consequent[0], antecedent[0]} <= {'==', '<=', '<'}:
        return False
    if consequent[0] == '==' and antecedent[0] != '==':
        return False
    op1, c1, poly1 = get_polyc(antecedent)
    op2, c2, poly2 = get_polyc(consequent)
    print('Checking entailment in Z: %s ==> %s' % ((op1, c1, poly1), (op2, c2, poly2)))
    if op2 == '==':
        return (c2, poly2) == (c1, poly1)
    return poly2 == poly1 and c1 <= c2

def match(bindings, e1, e2):
    """
    Extends the bindings so that subst(bindings, e1) == e2, or raises a ProofError.
    """
    if e1[0] == 'var':
        x = e1[1]
        if x in bindings:
            if e2 != bindings[x]:
                raise ProofError("Match failure: expected: %s; found: %s" % (bindings[x], e2))
        else:
            bindings[x] = e2
    else:
        if e1[0] != e2[0]:
            raise ProofError("Match failure: %s is not of the form %s" % (e2, e1))
        if e1[0] in {'==>', 'and', '==', '<=', '<', '+', '-'}:
            match(bindings, e1[1], e2[1])
            match(bindings, e1[2], e2[2])
        elif e1[0] == 'call':
            if e1[1] != e2[1]:
                raise ProofError("Match failure: %s is not of the form %s" % (e2, e1))
            for arg1, arg2 in zip(e1[2], e2[2]):
                match(bindings, arg1, arg2)
        elif e1[0] == 'number':
            if e1 != e2:
                raise ProofError("Match failure: expected: %s; found: %s" % (e1, e2))
        else:
            raise ProofError("match: construct not supported: %s" % e1)

def subst(e, bindings):
    if e[0] == 'var':
        return bindings[e[1]]
    elif e[0] in {'==>', 'and', '==', '<=', '<', '+', '-'}:
        return (e[0], subst(e[1], bindings), subst(e[2], bindings))
    elif e[0] == 'call':
        return ('call', e[1], tuple(map(lambda arg: subst(arg, bindings), e[2])))
    elif e[0] == 'number':
        return e
    else:
        raise ProofError("subst: construct not supported: %s" % (e,))

def normalize(eq):
    if eq[0] == '==' and eq[2] < eq[1]:
        return ('==', eq[2], eq[1])
    return eq

laws = {}

def check_entailment(line, antecedent, consequent, justification):
    def get_conjunct(i):
        if i < 1 or len(antecedent) < i:
            raise ProofError("Line %d: Antecedent conjunct index out of range in antecedent %s" % (line, antecedent))
        return antecedent[i - 1]

    print("Checking entailment %s ==> %s" % (antecedent, consequent))

    if justification[0] == 'Herschrijven':
        _, i, j = justification
        equation = get_conjunct(i)
        target = get_conjunct(j)
        if equation[0] != '==':
            raise ProofError("Kan niet herschrijven met " + str(equation) + " want is geen gelijkheid")
        rewrites = get_rewrites(target, equation[1], equation[2])
        for conjunct in consequent:
            if not (conjunct in antecedent or conjunct in rewrites):
                raise ProofError("Conjunct niet bewezen: " + str(conjunct) + " (rewrites = " + str(rewrites) + ")")
    elif justification[0] == 'Z':
        if justification[1] == None:
            for conjunct in consequent:
                if not (conjunct in antecedent or is_tautology(conjunct)):
                    raise ProofError("Conjunct niet bewezen: " + str(conjunct))
        else:
            antecedent_conjunct = get_conjunct(justification[1])
            for conjunct in consequent:
                if not (conjunct in antecedent or follows_in_Z_from(conjunct, antecedent_conjunct)):
                    raise ProofError("Conjunct niet bewezen: " + str(conjunct))
    elif justification[0] == 'law':
        _, lawName, indices = justification
        rule = laws[lawName]
        conclusion = rule
        premisses = []
        while conclusion[0] == '==>':
            premisses.append(conclusion[1])
            conclusion = conclusion[2]
        if len(indices) != len(premisses):
            raise ProofError("Verantwoording: verwacht %d conjunct-indices; slechts %d gegeven" % (len(premisses), len(indices)))
        variableBindings = {}
        for premiss, i in zip(premisses, indices):
            match(variableBindings, premiss, get_conjunct(i))
        instantiatedConclusion = subst(conclusion, variableBindings)
        print('Instantiated conclusion: ', instantiatedConclusion)
        for conjunct in consequent:
            if not (conjunct in antecedent or normalize(conjunct) == normalize(instantiatedConclusion)):
                raise ProofError("Conjunct niet bewezen: " + str(conjunct))
    else:
        raise ProofError("Verantwoording niet ondersteund: " + str(justification))

def checkProof(proof):
    if proof == []:
        raise ProofError("Need at least one assert")
    antecedent = get_conjuncts(proof[0][1])
    i = 1
    while i < len(proof):
        line, consequent, justification = proof[i]
        consequent = get_conjuncts(consequent)

        check_entailment(line, antecedent, consequent, justification)

        antecedent = consequent
        i += 1

text = '''
assert 0 <= n and i == 0
assert i <= n # Herschrijven met 2 in 1

assert i == 0
assert i == 0 and 1 <= 0 + 1 # Z
assert 1 <= i + 1 # Herschrijven met 1 in 2

assert i <= n and i < n
assert i + 1 <= n # Z op 2

# Wet Max1: y <= x ==> max(x, y) == x
# Wet Max2: x <= y ==> max(x, y) == y

assert True and x < y
assert x <= y # Z op 2
assert y == max(x, y) # Max2 op 1
'''
lexer = Lexer(text)
while True:
    token = lexer.next_token()
    print("'%s': '%s'" % (token, lexer.get_token_value()))
    if token == 'EOF':
        break

parser = Parser(text)
while parser.tokenType != 'EOF':
    if parser.tokenType == 'EOL':
        parser.eat()
    elif parser.tokenType == '#':
        name, rule = parser.parseLaw()
        laws[name] = rule
    else:
        proof = parser.parseProof()
        print(proof)
        checkProof(proof)