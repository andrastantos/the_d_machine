from constants import *
from typing import *

def _make_signed(data: int, bit_size: int) -> int:
    mask = (1 << bit_size) - 1
    sign_mask = 1 << (bit_size -1)
    data &= mask
    if data & sign_mask != 0:
        # negative, we calculate the absolute value,
        # then negate that to restore the proper signage
        return -((~data + 1) & mask)
    else:
        return data

opa_names = {
    OPA_PC: "$pc",
    OPA_SP: "$sp",
    OPA_R0: "$r0",
    OPA_R1: "$r1"
}

def _format_opa(opa: int) -> str:
    return opa_names[opa]

opb_formats = {
    OPB_MEM_IMMED_PC: "[$pc{s}{}]",
    OPB_MEM_IMMED_SP: "[$sp{s}{}]",
    OPB_MEM_IMMED_R0: "[$r0{s}{}]",
    OPB_MEM_IMMED: "[{}]",
    OPB_IMMED_PC: "$pc{s}{}",
    OPB_IMMED_SP: "$sp{s}{}",
    OPB_IMMED_R0: "$r0{s}{}",
    OPB_IMMED: "{}",
}

def _format_opb(opb: int, immed: int) -> str:
    sign = "+" if immed > 0 else ""
    return opb_formats[opb].replace("{s}",sign).replace("{}", str(immed))

inst_formats = {
    INST_SWAP  : ("SWAP {opa}, {opb}", "SWAPI {opa}, {opb}"),
    INST_OR    : ("OR {opa}, {opb}", "OR {opb}, {opa}"),
    INST_AND   : ("AND {opa}, {opb}", "AND {opb}, {opa}"),
    INST_XOR   : ("XOR {opa}, {opb}", "XOR {opb}, {opa}"),
    INST_UNK   : ("**** UNK **** {opa}, {opb}", "**** UNK **** {opb}, {opa}"),
    INST_ADD   : ("ADD {opa}, {opb}", "ADD {opb}, {opa}"),
    INST_SUB   : ("SUB {opa}, {opb}", "ISUB {opb}, {opa}"),
    INST_ISUB  : ("ISUB {opa}, {opb}", "SUB {opb}, {opa}"),
    INST_MOV   : ("MOV {opa}, {opb}", "MOV {opb}, {opa}"),
    INST_ISTAT : ("ISTAT {opa}", "ISTAT {opb}"),
    INST_ROR   : ("ROR {opa}", "ROR {opb}"),
    INST_ROL   : ("ROL {opa}", "ROL {opb}"),
    INST_EQ    : ("IF_EQ {opa}, {opb}", "IF_NEQ {opa}, {opb}"),
    INST_LTU   : ("IF_LTU {opa}, {opb}", "IF_GEU {opa}, {opb}"),
    INST_LTS   : ("IF_LTS {opa}, {opb}", "IF_GES {opa}, {opb}"),
    INST_LES   : ("IF_LES {opa}, {opb}", "IF_GTS {opa}, {opb}"),
}

def disasm_inst(inst: int) -> str:
    inst_field_opcode = (inst >> OPCODE_OFS) & OPCODE_MASK
    inst_field_d = (inst >> D_OFS) & D_MASK
    inst_field_opb = (inst >> OPB_OFS) & OPB_MASK
    inst_field_opa = (inst >> OPA_OFS) & OPA_MASK
    raw_inst_field_immed = (inst >> IMMED_OFS) & IMMED_MASK
    inst_field_immed = _make_signed(raw_inst_field_immed, IMMED_MASK.bit_length())
    opa_str = _format_opa(inst_field_opa)
    opb_str = _format_opb(inst_field_opb, inst_field_immed)
    disasm = inst_formats[inst_field_opcode][inst_field_d].replace("{opa}", opa_str).replace("{opb}", opb_str)
    return disasm

