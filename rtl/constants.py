from enum import Enum

class BusCmds(Enum):
    idle                 = 0
    read                 = 1
    write                = 2

class AluCmds(Enum):
    alu_add                 = 0
    alu_nor                 = 1
    alu_nand                = 2
    alu_xor                 = 3
    alu_ror                 = 4
    alu_rol                 = 5

class LBusDSelect(Enum):
    bus_d = 0
    alu_result = 1
    l_alu_result = 2

class AluASelect(Enum):
    pc = 0
    sp = 1
    r0 = 2
    r1 = 3
    zero = 4
    int_stat = 5
    l_bus_d = 6
    #l_bus_a = 7

class AluBSelect(Enum):
    immed = 0
    zero = 1
    l_bus_d = 2
    l_bus_a = 3
    one = 4

# Values for instruction fields
OPA_PC = 0b00
OPA_SP = 0b01
OPA_R0 = 0b10
OPA_R1 = 0b11

OPB_MEM_IMMED_PC = 0b000
OPB_MEM_IMMED_SP = 0b001
OPB_MEM_IMMED_R0 = 0b010
OPB_MEM_IMMED    = 0b011
OPB_IMMED_PC =     0b100
OPB_IMMED_SP =     0b101
OPB_IMMED_R0 =     0b110
OPB_IMMED =        0b111

OPB_CLASS_IMM = 0b1
OPB_CLASS_MEM = 0b0

# Binary ops
INST_SWAP  = 0b0000
INST_OR    = 0b0001
INST_AND   = 0b0010
INST_XOR   = 0b0011
INST_UNK   = 0b0100
INST_ADD   = 0b0101
INST_SUB   = 0b0110
INST_ISUB  = 0b0111
# Unary ops
INST_MOV   = 0b1000
INST_ISTAT = 0b1001
INST_ROR   = 0b1010
INST_ROL   = 0b1011
# Predicate ops (their inverse comes from the 'D' bit)
INST_EQ   = 0b1100
INST_LTU  = 0b1101
INST_LTS  = 0b1110
INST_LES  = 0b1111

INST_GROUP_UNARY = 0b10
INST_GROUP_PREDICATE = 0b11

DEST_REG = 0b0
DEST_MEM = 0b1

PRED_AS_IS = 0b0
PRED_INVERT = 0b1

OPCODE_MASK = 0b1111
D_MASK = 0b1
OPB_MASK = 0b111
OPA_MASK = 0b11
IMMED_MASK = 0b111111

OPCODE_OFS = 12
OPCODE_SIZE = 4
D_OFS = 11
D_SIZE = 1
OPB_OFS = 8
OPB_SIZE = 3
OPA_OFS = 6
OPA_SIZE = 2
IMMED_OFS = 0
IMMED_SIZE = 6

