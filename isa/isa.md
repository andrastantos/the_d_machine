ISA overview
============

This is a two-address ISA. One of the operands is a memory location or immediate, the other is a register.
The instruction set allows for read-modify-write of either (or both) operands.

NOTE: read-modify-write for core memories is practically free due to the destructive nature of reads. The memory controller doesn't do automatic write-backs (to save a data-register) so the CPU needs to make sure it happens.

Every instruction takes 8 clock cycles. A memory read or write takes two cycles each (to allow the column-select transient to settle in the core memory). Since a write *must* follow a read, a memory access is four cycles. With one argument coming from memory, 8 is the minimum execution period for an instruction; in other words, the execution speed is memory limited, no (significant) gain can be had from variable execution times. Also, since these 8 cycles completely saturate the memory bus, pipelining or other parallel tricks to increase IPC are pointless, even if they were possible in a transistor-based implementation (which they are not).

NOTE: I think it's best to do a bit-serial implementation where each of the 8 cycles are broken up into 16 micro-cycles. This allows for most buses to be 1-bit wide, muxes to be much cheaper, the ALU to be a single-bit one and most registers be turned into shift-registers.

Registers
-----------
- R0
- R1
- SP
- PC

Addressing modes
-----------------
- Immediate (sign-extended)
- register-relative
- register-relative immediate

CPU organization
----------------

The CPU is build around an ALU. The ALU has input registers for all of its inputs. These registers are:
- REG_ALU_A
- REG_ALU_B
- REG_ALU_CMD

The output is not registered.

The system bus outputs (address, data, control signals) are also registered.
- REG_BUS_A
- REG_BUS_D
- REG_BUS_CMD

The system bus input (BUS_D) is not registered.

Finally there's the register bank for the 4 registers.
- REG_PC
- REG_SP
- REG_R0
- REG_R1

There's an instruction register holding the currently executing instruction
- REG_INST

The following mode registers are also needed:
- INTDIS: set when interrupts are disabled
- INHIBIT: set when interrupts are inhibited (due to a predicate that disabled the following instruction)
- REG_ICYCLE: a 3-bit counter (or an 8-bit one-hot counter?) to time the execution phases of an instruction

Operation in each cycle
------------------------

Cycle 1:
- write ALU_RESULT into REG_PC
- write ALU_RESULT to REG_BUS_A
- write READ_1 into REG_BUS_CMD

Cycle 2:
- write READ_2 into REG_BUS_CMD

Cycle 3:
- write BUS_D into REG_BUS_D
- Load the REG_INST:
  - if INHIBIT is 1, load 16b0_100_0_011_00_000000 (i.e. OR PC with 0, i.e. NOP)
  - else if INTDIS is 0 and INT is 0 (i.e. there's an enabled and pending interrupt), load 0x0000
  - else write BUS_D into INST
- write WRITE_1 into REG_BUS_CMD
- clear INHIBIT (this can be moved to any subsequent cycle, if needed)

Cycle 4:
- Calculate sum of index register and immediate:
  - write REG_INST IMMED field into REG_ALU_B
  - write REG_INST OPB-selected value into REG_ALU_A
  - write ADD;C=0 into REG_ALU_CMD
- write WRITE_2 into REG_BUS_CMD

Cycle 5:
- write ALU_RESULT into REG_BUS_A
- write READ_1 into REG_BUS_CMD, if needed

Cycle 6:
- write READ_2 into REG_BUS_CMD, if needed

Cycle 7:
- Write BUS_D into REG_BUS_D
- Execute instruction:
  - write BUS_D or BUS_A into REG_ALU_B, depending on addressing mode
  - write register content or 0 into REG_ALU_A, depending on OPA field of INST
  - write REG_ALU_CMD based on OPCODE or 'OR' if we won't write data (i.e. we get the original data out)
- write WRITE_1 into BUS_CMD, if needed

Cycle 8:
- Write back result into CPU state:
  - write ALU_RESULT into selected register, if required based on INST
  - set INHIBIT, if needed
  - flip INTDIS, if needed
- Increment PC:
  - write PC in REG_ALU_A
  - write 0 into REG_ALU_B
  - write ADD into REG_ALU_CMD
  - set carry-in to 1 if PC is not the target register, otherwise set it to 0
- Write back result into memory:
  - write ALU_RESULT into BUS_D, if required based on INST
  - write WRITE_2 into BUS_CMD, if needed

NOTE: we assume that memory only needs correct data in WRITE_2. In other words, the inhibit lines are only activated with row-select, which, I think is fair.


Instruction encoding
---------------------

General instruction format:

```
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
|       OPCODE      |    OPB    |  OPA  |         IMMED         |
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
```

OPA codes (i.e. where does the first operand come from):
- 2b00 - PC
- 2b01 - SP
- 2b10 - R0
- 2b11 - R1

OPB input codes (i.e. where does the second operand come from):
- 3b000 - IMMED+PC
- 3b001 - IMMED+SP
- 3b010 - IMMED+R0
- 3b011 - IMMED
- 3b100 - MEM[ IMMED+PC ]
- 3b101 - MEM[ IMMED+SP ]
- 3b110 - MEM[ IMMED+R0 ]
- 3b111 - MEM[ IMMED+R1 ]

BINARY group

```
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
| 0 |    B_OP   | D |    OPB    |  OPA  |         IMMED         |
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
```

B_OP codes:
- 3b000 - SWAP <-- this one is weird as it writes both operands
- 3b001 - MOV
- 3b010 - ADD
- 3b011 - SUB
- 3b100 - OR
- 3b101 - AND
- 3b110 - XOR
- 3b111 - ROR/INTSTAT <-- this one is also weird as it uses 'D' to encode two different operations

NOTE: SWAP is special in several ways:
- It writes both operands. This means that the 'D' bit is meaningless and can be re-purposed as follows:
  - If 'D' is set to 0, it forces OPB to be IMMED or MEM[ IMMED ], in other words, it blocks the load of the base register into the ALU in cycle 4. In this case the INTDIS bit is also flipped during execution.
  - If 'D' is set to 1, normal SWAP operation is performed.

NOTE: ROR is special in that it can only rotate register operands (i.e. OPA). If D is set, it turns into the INTSTAT operation: INT in bit 0, INTDIS in bit 1

D codes:
- 1b0 - reg is destination
- 1b1 - memory is destination

PREDICATE group

```
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
| 1 | 0 |    P_OP   |    OPB    |  OPA  |         IMMED         |
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
```

in this case, we do all operations as if we were doing a SUB and see what the result would be
Note: all comparisons are assumed signed.

P_OP codes:
- 3b000 - ==0
- 3b001 - !=0
- 3b010 - <0  (unsigned)
- 3b011 - >=0 (unsigned)
- 3b110 - <0  (signed)
- 3b111 - >=0 (signed)
- 3b100 - <=0 (signed)
- 3b101 - >0  (signed)

These instructions test the condition and if it is satisfied, set INHIBIT bit. This bit disables interrupts for the next instruction as well as force that instruction to be replaced by a NOP. This allows any instruction to be conditional.

Interrupts and reset
-----------------------

- When an interrupt happens, PC is swapped with the content of address 0. The encoding is such that this is instruction 0x0000.

  Simply put, when an interrupt happens, the INST register is forced to 0 cycle 3. Because of this, the saved PC points to the instruction that needs to be retried once the interrupt handler returns.

  Any SWAP with the 'D' bit cleared also inverts INTDIS. This facilitates return from interrupt operations: in an atomic operation, we restore the execution to where it got interrupted while also enabling interrupts. Interrupts are immediately enabled, so if there's a pending interrupt, no forward progress is made. This is a minor price to pay for simplicity.

- reset is done the same way as interrupts, in other words, on reset, INST is forced to 0x0000 and ICYCLE is forced to 4.

- one can enable/disable interrupts by storing the subsequent location of execution in some convenient low address (something that an IMMED field can address), then performing the requisite SWAP operation (with the D bit cleared). By convention MEM[ 1 ] is used for this purpose.

- The interrupt status as well as the INTDIS bit can be checked by the INT_STAT unary operation.

Pseudo instructions
---------------------

NOP:
- this can be achieved by for example OR-ing a register with an immediate value of 0.

High level language support
-------------------------------

Function calls and returns:
- The stack frame needs to be prepared by the caller by SP-relative MOV-s (or other means storing the arguments on the stack)
- The return address is stored in the stack by a MOV. This cannot be done directly from the PC Since the PC as that doesn't yet point to the right instruction. There is a special addressing mode (PC+immediate) that can be used to calculate the return address and be stored in a different register, say R1. This value then can be stored in the stack.
- SP is incremented to point to the memory location *after* the return address.
- The function is called by loading its address into the PC.
- The called function allocates its frame on the stack (advancing SP in the process); executed and accesses local variables as well as arguments by SP-relative addressing.
- Prior to return the stack is restored
- The PC is loaded using SP-relative addressing, which returns execution to the caller
- The caller adjusts SP to remove arguments from the stack

Potential optimizations to function calls:
- We could require that arguments are freed by the callee, but that makes variable argument passing convoluted *and* that the return address is put on the stack before all arguments, not after.
- We could pass arguments as well as the return value in registers
- We could even say that R1 is a link register, containing the return address and require the callee to store it in it's own stack-frame, if needed. This, combined with R0 being an argument/return value register could be relatively efficient.

Miscellaneous quirks
------------------------

Arbitrary loads/stores/jumps:
- A full 16-bit immediate can be put in the code segment and loaded in a single instruction using PC-relative addressing. The offsets for these locations are a bit small (+/-32 locations), so one might have to jump over such constant sections to not run out of space. These jumps are also PC-relative (i.e. load PC with PC+IMMED), but that doesn't seem to be a big limitation: we could have 32 long immediates bunched up like that but it's unlikely that there are more than 32 instructions *within* 32 locations away from that section that need long immediates. The overhead seems rather minimal: one extra instruction every 32 or so operations is a 3% penalty.

Special addresses:
- Address 0 is the reset/interrupt vector.
- Address 1 is (by convention) used as a scratch-pad register for enabling/disabling interrupts

Input/Output
-------------

I/O is memory mapped. One thing that needs to be contended with is the pernicious read-modify-write behavior of the CPU. This puts some restrictions on how I/O can be designed.

Many peripheral chips are not friendly to this bus behavior. However, we're talking about a transistor computer, so peripherals are by necessity one-off, custom designs. In that case, this quirk of the CPU bus can be accommodated.

System design
===============

Not quite sure how, but a simple boot-loader will be needed that is swapped into the instruction space upon reset (based on some jumper or something). This ROM would only be consulted during the instruction fetch cycles (cycles 1-4), reads and writes would still go to core memory. This swapping will be controlled by a single bit that can be written (memory-mapped I/O) to disable the boot ROM and enable full access to memory.

Alternatively, we could say that the boot ROM is omni-present, and simple don't use the first few memory locations for code, only for data.

Either way, the kind of memory cycle (fetch v.s. read/write) will need to be communicated to the memory subsystem.

The control signals to the memory include:

- ADDRESS (generated by REG_BUS_A)
- DATA (generated by REG_BUS_D)
- READ_1
- READ_2
- WRITE_1
- WRITE_2
- FETCH

The expectation is that DATA is valid for reads the cycle after READ_2 goes active and *on the same cycle* when WRITE_2 is active.

The default behavior is that READ_1, READ_2, WRITE_1 and WRITE_2 are sequenced one after the other.

Registers are to be avoided as they are very expensive, instead, latches are used wherever possible. This is tricky though and needs way more thought.

In terms of peripherals, I'm thinking about the following:
- A simple serial port, probably 9600 baud or something, maybe HW handshake?
- A tape drive - this one I hope could be a 4-track casette tape with full electronic control. The signal would be FM modulated (per https://en.wikipedia.org/wiki/Kansas_City_standard), probably in the 1200baud variant. The bit organization would be 4 symbols (4 bits each) for a 16-bit word. These would be grouped into blocks of 256 words. Each block would have a 16-bit checksum in the end, a sync sequence at the beginning. This, at 1200baud would give a data-rate of 0.6kBytes/s. Since we have 32k of RAM, even the largest program would load in about a minute. A 60minute tape would have a capacity of more than a megabyte.
- I'm wondering if any/all of this can be bit-banged?