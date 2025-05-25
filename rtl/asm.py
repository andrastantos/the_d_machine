# A very simply assembler

from constants import *
from typing import *
from abc import abstractmethod
import re

opa_reg_names = {
    "$pc": OPA_PC,
    "$sp": OPA_SP,
    "$r0": OPA_R0,
    "$r1": OPA_R1
}

opb_mem_reg_names = {
    "$pc": OPB_MEM_IMMED_PC,
    "$sp": OPB_MEM_IMMED_SP,
    "$r0": OPB_MEM_IMMED_R0
}

opb_immed_reg_names = {
    "$pc": OPB_IMMED_PC,
    "$sp": OPB_IMMED_SP,
    "$r0": OPB_IMMED_R0,
}

class AsmError(Exception):
    def __init__(self, message: str):
        self.message = message
    def __str__(self) -> str:
        return str(self.message)

class SymbolTable(object):
    def __init__(self):
        self.table: Dict[str, Union[int, Expression]] = OrderedDict()
        self.resolved = True
    def add(self, name: str, value: 'Expression'):
        if name in self.table:
            raise AsmError(f"Symbol {name} is already defined as {self.table[name]}")
        self.table[name] = value
        self.resolved = False
    def get(self, name):
        return self.table[name]
    def resolve(self):
        if self.resolved: return
        # Each table entry is a list of (tokenized) strings for the 'value' field. So each element is either:
        #
        # Our goal is to find symbols that can be evaluated down to a single integer, replace the value with that integer value
        # and repeat the process until we either can't make further progress or we don't have anything to do.
        # We are using pythons eval function to do the heavy-lifting for us.
        table_changed = True
        resolved_symbols: Dict[str, int] = {}
        unresolved_symbols: Dict[str, Expression] = {}
        for sym_name, sym_value in self.table.items():
            if _is_int(sym_value):
                resolved_symbols[sym_name] = int(sym_value)
                continue
            try:
                resolved_symbols[sym_name] = int(" ".join(sym_value.token_list))
            except ValueError:
                unresolved_symbols[sym_name] = sym_value
        while table_changed:
            table_changed = False
            for sym_name, sym_value in unresolved_symbols.items():
                try:
                    resolved_value = eval(" ".join(sym_value.token_list), resolved_symbols)
                    try:
                        int_value = int(resolved_value)
                    except ValueError:
                        raise AsmError(f"Symbol {sym_name} with resolved value {resolved_value} doesn't evaluate to an integer")
                    resolved_symbols[sym_name] = int_value
                    del unresolved_symbols[sym_name]
                    table_changed = True
                    break
                except NameError:
                    continue
        if len(unresolved_symbols) > 0:
            raise AsmError(f"Can't resolve symbol(s) {' ,'.join(unresolved_symbols.keys())}")
        self.table = resolved_symbols
        self.resolved = True

class Expression(object):
    def __init__(self, token_list: Sequence[str]):
        self.token_list = token_list

    def value(self, symbol_table: SymbolTable):
        try:
            return self.resolved_value
        except AttributeError:
            symbol_table.resolve() # This will be fast if already resolved
            try:
                expr = " ".join(self.token_list)
                self.resolved_value = eval(expr, symbol_table.table)
            except SyntaxError:
                raise AsmError(f"Can't evaluate constant expression: '{expr}'. Did you use $r1 as the base register?")
            return self.resolved_value



class InstructionBase(object):
    @abstractmethod
    def machine_code(self, symbol_table: SymbolTable) -> Sequence[int]:
        pass
    @abstractmethod
    def get_size(self) -> int:
        pass

class Instruction(InstructionBase):
    def __init__(self, opcode, d, opa, opb, immed: Expression):
        self.opcode = opcode
        self.d = d
        self.opa = opa
        self.opb = opb
        self.immed = immed
    def machine_code(self, symbol_table: SymbolTable) -> Sequence[int]:
        immed = self.immed.value(symbol_table)
        if (immed > (IMMED_MASK >> 1)) or (immed < (-IMMED_MASK >> 1)):
            raise AsmError(f"Immediate value {immed} is out of range")
        inst_code = (self.opcode << OPCODE_OFS) | (self.d << D_OFS) | (self.opb << OPB_OFS) | (self.opa << OPA_OFS) | ((immed & IMMED_MASK) << IMMED_OFS)
        return (inst_code, )
    def get_size(self) -> int:
        return 1;

class PseudoOpWord(InstructionBase):
    def __init__(self, values: Sequence[Expression]):
        self.values = values
    def machine_code(self, symbol_table: SymbolTable) -> Sequence[int]:
        int_vals = tuple(val.value(symbol_table) for val in self.values)
        for val in int_vals:
            if (val.bit_length() > 16):
                raise AsmError(f"Value {val} doesn't fit in 16 bits")
        return list(int_vals)
    def get_size(self) -> int:
        return len(self.values)
class PseudoOpString(InstructionBase):
    def __init__(self, value: str):
        bytes = list(value.encode())
        bytes.append(0) # zero terminate string
        if len(bytes) & 1 != 0: bytes.append(0)
        words = list(bytes[i:i+2] for i in range(0, len(bytes), 2))
        self.value = words
    def machine_code(self, symbol_table: SymbolTable) -> Sequence[int]:
        return self.values
    def get_size(self) -> int:
        return len(self.values)


_tokenizer_re = re.compile(r'(?=[\, \[\]\+\-\*\/\(\)\&\|\~\;])|(?<=[\, \[\]\+\-\*\/\(\)\&\|\~\;])')

def tokenize(line: str) -> Sequence[str]:
    raw_tokens = re.split(_tokenizer_re, line)
    tokens = list(tok for tok in raw_tokens if tok.strip() != "")
    # Remove any comments
    try:
        tokens = tokens[:tokens.index(';')]
    except ValueError:
        pass
    return tokens

def _is_int(s):
    try:
        int(s)
        return True
    except TypeError:
        return False
    except ValueError:
        return False

def parse_constant_expression(line: Sequence[str], cursor: int, *, force_plus: bool):
    if force_plus and line[cursor] not in "+-":
        raise AsmError(f"constant offset must start with + or -")
    # We simply find the end of the expression and stuff it into an Expression object
    start = cursor
    for token in line[start:]:
        cursor += 1
        if token in "],":
            cursor -= 1
            break
    exp = Expression(line[start:cursor])
    return exp, cursor
    '''
    sign = -1 if line[cursor] == '-' else 1
    if line[cursor] in "+-":
        cursor += 1
    if _is_int(line[cursor]):
        immed = int(line[cursor])
        cursor += 1
    else:
        # TODO: this is where we would add a symbol reference to be resolved later
        raise AsmError(f"constant {line[cursor]} is not numeric")
    return sign * immed, cursor
    '''

def parse_opb(line: Sequence[str], cursor: int, *, allow_immed: bool):
    if line[cursor] == "[":
        cursor += 1
        if line[cursor] not in opb_mem_reg_names:
            immed, cursor = parse_constant_expression(line, cursor, force_plus=False)
            opb = OPB_MEM_IMMED
            if line[cursor] != "]":
                raise AsmError(f"memory reference is not terminated properly")
            cursor += 1
        else:
            immed = Expression("0")
            opb = opb_mem_reg_names[line[cursor]]
            cursor += 1
            if line[cursor] == "]":
                cursor += 1
            else:
                immed, cursor = parse_constant_expression(line, cursor, force_plus=True)
                if line[cursor] != "]":
                    raise AsmError(f"memory reference is not terminated properly")
                cursor += 1
    elif allow_immed:
        if line[cursor] in opb_immed_reg_names:
            opb = opb_immed_reg_names[line[cursor]]
            cursor += 1
            if cursor == len(line):
                immed = Expression("0")
            else:
                immed, cursor = parse_constant_expression(line, cursor, force_plus=True)
        else:
            opb = OPB_IMMED
            immed, cursor = parse_constant_expression(line, cursor, force_plus=False)
    else:
        raise AsmError(f"{line[cursor]} is invalid as a operand B")

    return opb, immed, cursor


def parse_dual_arg(inst_code: int, line: Sequence[str], *, is_swapi = False) -> Instruction:
    # The line should be in the form of:
    #                D        OPA         OPB                  IMMED
    # ---------------------------------------------------------------
    # $pc, $sp       0        OPA_PC      OPB_IMMED_SP         0
    # $pc, $r0+3     0        OPA_PC      OPB_IMMED_R0         3
    # $r1, -12       0        OPA_R1      OPB_IMMED            -12
    # $r0, [$sp]     0        OPA_R0      OPB_MEM_IMMED_SP     0
    # $sp, [$r0-12]  0        OPA_SP      OPB_MEM_IMMED_R0     -12
    # $sp, [12]      0        OPA_SP      OPB_MEM_IMMED        12
    # [$r0], $pc     1        OPA_PC      OPB_MEM_IMMED_R0     0
    # [$sp-2], $r0   1        OPA_R0      OPB_MEM_IMMED_SP     -2
    #
    # We can't describe the case where we would target an 'IMMED' field, but that's not a valid thing to do anyway
    # We will want to special-case SWAPI and allow for:
    # $r1, [3]       0        OPA_R1      OPB_MEM_IMMED_PC     3
    cursor = 1
    try:
        if line[cursor] == "[":
            d = 1
            opb, immed, cursor = parse_opb(line, cursor, allow_immed=False)
            if line[cursor] != ",":
                raise AsmError(f"there must be a comma after first operand")
            cursor += 1
            opa = opa_reg_names[line[cursor]]
            cursor += 1
        elif line[cursor] in opa_reg_names:
                d = 0
                opa = opa_reg_names[line[cursor]]
                cursor += 1
                if line[cursor] != ",":
                    raise AsmError(f"there must be a comma after first operand")
                cursor += 1
                opb, immed, cursor = parse_opb(line, cursor, allow_immed=True)
        else:
            raise AsmError(f"I don't understand the first argument")
    except IndexError:
        raise AsmError(f"Line is too short, can't understand it")
    if cursor != len(line):
        raise AsmError(f"Line is too long, can't understand it")
    return Instruction(inst_code, d, opa, opb, immed)

def parse_single_arg(inst_code: int, line: Sequence[str]) -> Instruction:
    # The line should be in the form of:
    #                D        OPA         OPB                  IMMED
    # ---------------------------------------------------------------
    # $pc            0        OPA_PC      OPB_IMMED_PC         0
    # [$r0]          1        OPA_PC      OPB_MEM_IMMED_R0     0
    # [$sp-2]        1        OPA_PC      OPB_MEM_IMMED_SP     -2
    #
    # We can't describe the case where we would target an 'IMMED' field, but that's not a valid thing to do anyway
    cursor = 1
    try:
        if line[cursor] == "[":
            d = 1
            opb, immed, cursor = parse_opb(line, cursor, allow_immed=False)
            opa = OPA_PC
        elif line[cursor] in opa_reg_names:
            d = 0
            opa = opa_reg_names[line[cursor]]
            cursor += 1
            opb = OPB_IMMED
            immed = Expression("0")
    except IndexError:
        raise AsmError(f"Line is too short, can't understand it")
    if cursor != len(line):
        raise AsmError(f"Line is too long, can't understand it")
    return Instruction(inst_code, d, opa, opb, immed)

def parse_swapi(inst_code: int, line: Sequence[str]) -> Instruction:
    inst = parse_dual_arg(inst_code, line, is_swapi=True)
    inst.d = 0
    return inst

def parse_swap(inst_code: int, line: Sequence[str]) -> Instruction:
    inst = parse_dual_arg(inst_code, line)
    inst.d = 1
    return inst

def parse_sub(inst_code: int, line: Sequence[str]) -> Instruction:
    inst = parse_dual_arg(inst_code, line)
    if inst.d:
        # the operands are swapped, this is encoded as an isub
        inst.opcode = INST_ISUB
        inst.d = 1
    else:
        inst.d = 0
    return inst

def parse_isub(inst_code: int, line: Sequence[str]) -> Instruction:
    inst = parse_dual_arg(inst_code, line)
    if inst.d:
        # the operands are swapped, this is encoded as an sub
        inst.opcode = INST_SUB
        inst.d = 1
    else:
        inst.d = 0
    return inst

def parse_eq(inst_code: int, line: Sequence[str]) -> Instruction:
    inst = parse_dual_arg(inst_code, line)
    inst.d = 0
    return inst

def parse_neq(inst_code: int, line: Sequence[str]) -> Instruction:
    inst = parse_dual_arg(inst_code, line)
    inst.d = 1
    return inst

def parse_pos_pred(inst_code: int, line: Sequence[str]) -> Instruction:
    inst = parse_dual_arg(inst_code, line)
    # If the arguments are swapped, we swap the test condition instead, but that's what 'd' already contains
    return inst

def parse_neg_pred(inst_code: int, line: Sequence[str]) -> Instruction:
    inst = parse_dual_arg(inst_code, line)
    # If the arguments are swapped, we swap the test condition instead
    inst.d = ~inst.d
    return inst


class InstParser(object):
    def __init__(self, opcode, parser):
        self.opcode = opcode
        self.parser = parser

    def parse(self, line: Sequence[str], context: 'AsmContext'):
        inst = self.parser(self.opcode, line)
        context.add_inst(inst)

class WordParser(object):
    def __init__(self):
        pass
    def parse(self, line: Sequence[str], context: 'AsmContext'):
        # items are separated by commas
        value = []
        values = []
        for token in line[1:]:
            if token == ',':
                if len(value) > 0:
                    values.append(Expression(value))
                else:
                    values.append(Expression("0"))
                value.clear()
            else:
                value.append(token)
        if len(value) > 0:
            values.append(Expression(value))
        context.add_inst(PseudoOpWord(values))

class StrParser(object):
    def __init__(self):
        pass
    def parse(self, line: Sequence[str], context: 'AsmContext'):
        raise AsmError("TODO: I don't know how to implement this: the tokenizer stripped all white-spaces inside strings...")

class DefParser(object):
    def __init__(self):
        pass
    def parse(self, line: Sequence[str], context: 'AsmContext'):
        # The syntax here is: .def SYMBOL=3+23
        cursor = 1
        symbol_name = line[cursor]
        cursor += 1
        if line[cursor] != '=':
            raise AsmError(".def needs an equal sign after symbol name")
        symbol_expression = Expression(line[cursor+1:])
        context.symbol_table.add(symbol_name, symbol_expression)


class LabelParser(object):
    def __init__(self):
        pass
    def parse(self, line: Sequence[str], context: 'AsmContext'):
        # The syntax here is: LABEL:
        cursor = 0
        symbol_name = line[cursor]
        cursor += 1
        if line[cursor] != ':':
            raise AsmError("labels must be terminated by a colon")
        symbol_expression = Expression(str(context.org))
        context.symbol_table.add(symbol_name, symbol_expression)

class SectionParser(object):
    def __init__(self):
        pass
    def parse(self, line: Sequence[str], context: 'AsmContext'):
        # The syntax here is: .section NAME [<number>] <-- here the number must be an expression that can be evaluated right away
        # If number is omitted, we continue with the existing section. Or create a new one with 0-base
        section_name = line[1]
        if (len(line) > 2):
            org = Expression(line[2:])
        else:
            if context.has_section(section_name):
                context.set_active_section(section_name)
            else:
                org = "0"
        context.symbol_table.resolve()
        context.set_active_section(section_name, org.value(context.symbol_table))

class Section(object):
    def __init__(self, base_addr: int):
        self.base_addr = base_addr
        self.org = base_addr
        self.objects: Dict[int, InstructionBase] = OrderedDict()

    def add_inst(self, inst:InstructionBase):
        self.objects[self.org] = inst
        self.org += inst.get_size()

    def set_org(self, org: int):
        self.org = org

    def machine_code(self, name: str, symbol_table: SymbolTable) -> Sequence[int]:
        ret_val = []
        for addr in sorted(self.objects):
            inst = self.objects[addr]
            inst_words = inst.machine_code(symbol_table)
            for ofs, word in enumerate(inst_words):
                inst_addr = addr + ofs - self.base_addr # This is the index into ret_val
                if inst_addr >= len(ret_val):
                    ret_val += (None,)*(inst_addr+1-len(ret_val))
                if ret_val[inst_addr] is not None:
                    raise AsmError(f"Multiple values are defined for address 0x{inst_addr+self.base_addr:04x} in section {name}")
                ret_val[inst_addr] = word
        return ret_val


class AsmContext(object):
    label_parser = LabelParser()

    instructions = {
        "swap":      InstParser(INST_SWAP,  parse_swap),
        "swapi":     InstParser(INST_SWAP,  parse_swapi),
        "or":        InstParser(INST_OR,    parse_dual_arg),
        "and":       InstParser(INST_AND,   parse_dual_arg),
        "xor":       InstParser(INST_XOR,   parse_dual_arg),
        "add":       InstParser(INST_ADD,   parse_dual_arg),
        "sub":       InstParser(INST_SUB,   parse_sub),
        "isub":      InstParser(INST_ISUB,  parse_isub),
        "mov":       InstParser(INST_MOV,   parse_dual_arg),
        "if_eq":     InstParser(INST_EQ,    parse_eq),
        "if_ltu":    InstParser(INST_LTU,   parse_pos_pred),
        "if_lts":    InstParser(INST_LTS,   parse_pos_pred),
        "if_les":    InstParser(INST_LES,   parse_pos_pred),
        "if_neq":    InstParser(INST_EQ,    parse_neq),
        "if_geu":    InstParser(INST_LTU,   parse_neg_pred),
        "if_ges":    InstParser(INST_LTS,   parse_neg_pred),
        "if_gts":    InstParser(INST_LES,   parse_neg_pred),
        "istat":     InstParser(INST_ISTAT, parse_single_arg),
        "rol":       InstParser(INST_ROL,   parse_single_arg),
        "ror":       InstParser(INST_ROR,   parse_single_arg),
        ".word":     WordParser(),
        ".section":  SectionParser(),
        ".def":      DefParser(),
    }

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.sections: Dict[Section] = OrderedDict()

    def has_section(self, name: str):
        return name in self.sections

    def set_active_section(self, name: str, org: Optional[int] = None):
        if name not in self.sections:
            self.sections[name] = Section(org if org is not None else 0)
        self.active_section: Section = self.sections[name]
        if org is not None:
            self.active_section.set_org(org)

    def add_inst(self, inst:InstructionBase):
        if not hasattr(self, "active_section"):
            raise AsmError("Can't start assembling without an active section. User the '.section' directive to define one")
        self.active_section.add_inst(inst)

    def parse_line(self, line: str) -> None:
        if len(line.strip()) == 0:
            return
        tokens = tokenize(line)
        if len(tokens) == 0:
            return
        if tokens[0].lower() in self.instructions:
            parser = self.instructions[tokens[0].lower()]
        else:
            # Check for labels:
            if tokens[1] == ':':
                parser = self.label_parser
            else:
                raise AsmError(f"Instruction {tokens[0]} is invalid")
        parser.parse(tokens, self)

    def compile(self, asm_source: str) -> Tuple[int, Sequence[int]]:
        # Assemble into 'object' file
        for line in asm_source.splitlines():
            self.parse_line(line)
        # Generate text for all sections
        section_texts = OrderedDict()
        for section_name, section in self.sections.items():
            text = section.machine_code(section_name, self.symbol_table)
            section_texts[section.base_addr] = text

        # Merge all sections into a single binary
        start_addr = min(section_texts)
        max_addr = max(base + len(text) for base, text in section_texts.items())
        ret_val = []
        ret_val += (None,)*(max_addr-start_addr)
        for base, text in section_texts.items():
            for ofs, word in enumerate(text):
                addr = base + ofs - start_addr
                if ret_val[addr] is not None:
                    raise AsmError(f"Overlapping sections at address 0x{addr+start_addr:04x}")
                ret_val[addr] = word
        # Finally replace all remaining None-s with 0-s in the binary
        ret_val = list(0 if val is None else val for val in ret_val)
        return start_addr, ret_val

def assemble(source: str) -> Tuple[int, Sequence[int]]:
    context = AsmContext()
    return context.compile(source)



if __name__ == "__main__":
    #parse("ADD $r0, $sp")
    #parse("SUB $r1, [$pc]")
    #parse("SUB $r1, [$r0-2]")
    #parse("SUB $r1, [$r0+23]")
    #parse("SWAPI $r1, [23]")
    #parse("SWAP $r1, [$pc-23]")
    #parse("XOR [$r0], $r1")
    #parse("XOR [$r0-2], $r1")
    #parse("XOR [$r0+22], $r1")
    #parse("ROL $r0")
    #parse("ROL [$sp]")
    #parse("ROL [$sp-2]")
    #parse("ROL [$sp+3]")
    #assemble(".section TEXT 0\n        ROL [$sp]")
    assemble(".section TEXT 0x1000\n   mov [$r1-1], $sp  ; should write to address 2")
