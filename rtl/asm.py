# A very simply assembler

# SWAP $PC, [$SP+3]

from constants import *
from typing import *
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
    "$r0": OPB_MEM_IMMED_R0,
    "$r1": OPB_MEM_IMMED_R1
}

opb_immed_reg_names = {
    "$pc": OPB_IMMED_PC,
    "$sp": OPB_IMMED_SP,
    "$r0": OPB_IMMED_R0,
}


_tokenizer_re = re.compile(r'(?=[\, \[\]\+\-\;])|(?<=[\, \[\]\+\-\;])')
#_tokenizer_re = re.compile(r'(?=[ ])|(?<=[ ])')

def tokenize(line: str) -> Sequence[str]:
    raw_tokens = re.split(_tokenizer_re, line)
    tokens = list(tok for tok in raw_tokens if tok.strip() != "")
    return tokens

def _is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def parse_dual_arg(inst_code: int, line: Sequence[str], d, *, is_swapi = False):
    # The line should be in the form of:
    #                D        OPA         OPB                  IMMED
    # ---------------------------------------------------------------
    # $pc, $sp       0        OPA_PC      OPB_IMMED_SP         0
    # $pc, $r0+3     0        OPA_PC      OPB_IMMED_R0         3
    # $r1, -12       0        OPA_R1      OPB_IMMED            -12
    # $r0, [$sp]     0        OPA_R0      OPB_MEM_IMMED_SP     0
    # $sp, [$r1-12]  0        OPA_SP      OPB_MEM_IMMED_R1     -12
    # [$r1], $pc     1        OPA_PC      OPB_MEM_IMMED_R1     0
    # [$sp-2], $r0   1        OPA_R0      OPB_MEM_IMMED_SP     -2
    #
    # We can't describe the case where we would target an 'IMMED' field, but that's not a valid thing to do anyway
    # We will want to special-case SWAPI and allow for:
    # $r1, [3]       0        OPA_R1      OPB_MEM_IMMED_PC     3
    initial_d = d
    cursor = 1
    if line[cursor] == "[":
        cursor += 1
        d = 1
        try:
            if line[cursor] not in opb_mem_reg_names: raise f"register name {line[cursor]} is invalid as a memory reference"
            opb = opb_mem_reg_names[line[cursor]]
            cursor += 1
            if line[cursor] == "]":
                immed = 0
                cursor += 1
            elif line[cursor] in "+-":
                try:
                    immed = int(line[cursor]+line[cursor+1])
                except ValueError:
                    raise f"offset value {line[cursor+1]} must be an integer"
                cursor += 2
                if line[cursor] != "]":
                    raise f"First argument must be terminated by ']'"
                cursor += 1
            else:
                raise f"offset value {line[cursor]} is invalid"
            if line[cursor] != ",":
                raise f"there must be a comma after first operand"
            cursor+=1
            if line[cursor] not in opa_reg_names:
                raise f"register name {line[cursor]} is invalid"
            opa = opa_reg_names[line[cursor]]
        except IndexError:
            raise f"Line is too short, can't understand it"
        if cursor+1 < len(line) and line[cursor+1] != ";":
            raise f"Line is too long, can't understand it"
    elif line[cursor] in opa_reg_names:
        try:
            d = 0
            opa = opa_reg_names[line[cursor]]
            if line[2] != ",":
                raise f"there must be a comma after first operand"
            cursor = 3
            if line[cursor] == "[":
                cursor += 1
                immed = 0
                if line[cursor] not in opb_mem_reg_names:
                    # Test for SWAPI special case
                    if is_swapi:
                        if _is_int(line[cursor]):
                            opb = OPB_MEM_IMMED_PC
                            immed = int(line[cursor])
                            cursor += 1
                        elif line[cursor] == "-" and _is_int(line[cursor+1]):
                            opb = OPB_MEM_IMMED_PC
                            immed = -int(line[cursor+1])
                            cursor += 2
                        else:
                            raise f"register name {line[cursor]} is invalid as a memory reference"
                    else:
                        raise f"register name {line[cursor]} is invalid as a memory reference"
                else:
                    opb = opb_mem_reg_names[line[cursor]]
                    cursor += 1
                if line[cursor] == "]":
                    cursor += 1
                elif line[cursor] in "+-":
                    try:
                        immed = int(line[cursor]+line[cursor+1])
                    except ValueError:
                        raise f"offset value {line[cursor+1]} must be an integer"
                    cursor += 2
                else:
                    raise f"offset value {line[cursor]} is invalid"
            elif line[cursor] in opb_immed_reg_names:
                opb = opb_immed_reg_names[line[cursor]]
                cursor += 1
                if cursor == len(line):
                    immed = 0
                elif line[cursor] in "+-":
                    try:
                        immed = int(line[cursor]+line[cursor+1])
                    except ValueError:
                        raise f"offset value {line[cursor+1]} must be an integer"
                    cursor += 2
                else:
                    raise f"offset value {line[cursor]} is invalid"
            elif _is_int(line[cursor]):
                opb = OPB_IMMED
                immed = int(line[cursor])
                cursor += 1
            elif line[cursor] == "-" and _is_int(line[cursor+1]):
                opb = OPB_IMMED
                immed = -int(line[cursor+1])
                cursor += 2
            else:
                raise f"register name {line[cursor]} is invalid as a second operand"
        except IndexError:
            raise f"Line is too short, can't understand it"
        if cursor+1 < len(line) and line[cursor+1] != ";":
            raise f"Line is too long, can't understand it"
    else:
        raise f"I don't understand the first argument"
    return inst_code, d ^ initial_d, opa, opb, immed


def parse_single_arg(inst_code: int, line: Sequence[str], d):
    # The line should be in the form of:
    #                D        OPA         OPB                  IMMED
    # ---------------------------------------------------------------
    # $pc            0        OPA_PC      OPB_IMMED_PC         0
    # [$r1]          1        OPA_PC      OPB_MEM_IMMED_R1     0
    # [$sp-2]        1        OPA_PC      OPB_MEM_IMMED_SP     -2
    #
    # We can't describe the case where we would target an 'IMMED' field, but that's not a valid thing to do anyway
    cursor = 1
    if line[cursor] == "[":
        d = 1
        cursor += 1
        opa = OPA_PC
        try:
            if line[cursor] not in opb_mem_reg_names: raise f"register name {line[cursor]} is invalid as a memory reference"
            opb = opb_mem_reg_names[line[cursor]]
            cursor += 1
            if line[cursor] == "]":
                immed = 0
                cursor += 1
            elif line[cursor] in "+-":
                try:
                    immed = int(line[cursor]+line[cursor+1])
                except ValueError:
                    raise f"offset value {line[cursor+1]} must be an integer"
                cursor += 2
            else:
                raise f"offset value {line[cursor]} is invalid"
        except IndexError:
            raise f"Line is too short, can't understand it"
        if cursor+1 < len(line) and line[cursor+1] != ";":
            raise f"Line is too long, can't understand it"
    elif line[1] in opa_reg_names:
        try:
            d = 0
            cursor = 1
            opb = OPB_IMMED
            opa = opa_reg_names[line[cursor]]
            immed = 0
            cursor += 1
        except IndexError:
            raise f"Line is too short, can't understand it"
        if cursor+1 < len(line) and line[cursor+1] != ";":
            raise f"Line is too long, can't understand it"
    return inst_code, d, opa, opb, immed

def parse_swapi(inst_code: int, line: Sequence[str], d):
    new_d, opa, opb, immed = parse_dual_arg(inst_code, line, False, is_swapi=True)
    return inst_code, 0, opa, opb, immed

def parse_swap(inst_code: int, line: Sequence[str], d):
    new_d, opa, opb, immed = parse_dual_arg(inst_code, line, False)
    return inst_code, 1, opa, opb, immed

def parse_sub(inst_code: int, line: Sequence[str], d):
    new_d, opa, opb, immed = parse_dual_arg(inst_code, line, False)
    if new_d:
        # the operands are swapped, this is encoded as an isub
        return INST_ISUB, 1, opa, opb, immed
    return inst_code, 0, opa, opb, immed

def parse_isub(inst_code: int, line: Sequence[str], d):
    new_d, opa, opb, immed = parse_dual_arg(inst_code, line, False)
    if new_d:
        # the operands are swapped, this is encoded as an sub
        return INST_SUB, 1, opa, opb, immed
    return inst_code, 0, opa, opb, immed

class inst_parser(object):
    def __init__(self, opcode, parser, d=0):
        self.opcode = opcode
        self.parser = parser
        self.d = d

    def parse(self, line: Sequence[str]):
        return self.parser(self.opcode, line, self.d)

instructions = {
    "swap":      inst_parser(INST_SWAP, parse_swap),
    "swapi":     inst_parser(INST_SWAP, parse_swapi),
    "or":        inst_parser(INST_OR, parse_dual_arg),
    "and":       inst_parser(INST_AND, parse_dual_arg),
    "xor":       inst_parser(INST_XOR, parse_dual_arg),
    "add":       inst_parser(INST_ADD, parse_dual_arg),
    "sub":       inst_parser(INST_SUB, parse_sub),
    "isub":      inst_parser(INST_ISUB, parse_isub),
    "mov":       inst_parser(INST_MOV, parse_dual_arg),
    "if_eq":     inst_parser(INST_EQ, parse_dual_arg, False),
    "if_ltu":    inst_parser(INST_LTU, parse_dual_arg, False),
    "if_lts":    inst_parser(INST_LTS, parse_dual_arg, False),
    "if_les":    inst_parser(INST_LES, parse_dual_arg, False),
    "if_ne":     inst_parser(INST_EQ, parse_dual_arg, True),
    "if_geu":    inst_parser(INST_LTU, parse_dual_arg, True),
    "if_ges":    inst_parser(INST_LTS, parse_dual_arg, True),
    "if_gts":    inst_parser(INST_LES, parse_dual_arg, True),
    "istat":     inst_parser(INST_ISTAT, parse_single_arg),
    "rol":       inst_parser(INST_ROL, parse_single_arg),
    "ror":       inst_parser(INST_ROR, parse_single_arg),
}

def parse(line: str) -> Optional[int]:
    if len(line.strip()) == 0:
        return None
    tokens = tokenize(line)
    if len(tokens) == 0:
        return None
    if tokens[0] == ";":
        return None
    if tokens[0].lower() not in instructions:
        raise f"Instruction {tokens[0]} is invalid"
    parser = instructions[tokens[0].lower()]
    opcode, d, opa, opb, immed = parser.parse(tokens)
    if (immed > (IMMED_MASK >> 1)) or (immed < (-IMMED_MASK >> 1)):
        raise f"Immediate value {immed} is out of range"
    inst_code = (opcode << OPCODE_OFS) | (d << D_OFS) | (opb << OPB_OFS) | (opa << OPA_OFS) | ((immed & IMMED_MASK) << IMMED_OFS)
    return inst_code

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
    parse("ROL $r0")
    parse("ROL [$sp]")
    parse("ROL [$sp-2]")
    parse("ROL [$sp+3]")
