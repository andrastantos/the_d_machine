Basic considerations
=====================

We have 3 ALU operations to perform for every instruction:

1. Increment PC
2. Compute memory reference (this needs instruction field)
3. Perform actual ALU operation

We also have 4 memory cycles to complete:

  a. Read instruction (this needs PC)
  b. Write instruction back
  c. Read operand (this needs memory reference)
  d. Write operand

'a' needs '1' and 'c' needs '2', while '2' needs '1'; also, if possible '2' and '3' needs to precede '1' so that PC-related operations reference the current PC, not the next one.

So, the cycles are:

Cycle    ALU op                            Memory op
======   ============================      ===========
1        -                                 Read instruction
2        Compute memory reference          Write instruction back
3        -                                 Read operand
4        Perform actual ALU operation      -
5        Increment PC                      Write operand

I don't think we can save any cycles here:

'2' needs '1' to complete for both of it's operations
'3' needs the memory reference, so it can't happen earlier
'4' needs the operand read, so again, can't happen before '3'
'5' needs '4' for the result to be ready.

The only way to save a cycle is if:

1. We don't allow write-back of ALU results, thus the write-back can happen during '4'
2. We give up on the PC pointing to the current instruction and increment the PC during '1'.

Given the very limited number of registers, if the are the only ones that can be a target for an instruction, we introduce a ton of spills into the code, which - at this rate - would take 4 cycles. So it's only worth it if there are no more than 25% extra spills introduced. That's hard to believe, actually, so I think I'll go with the 5-cycle implementation, however painful the non-power-of-two thing looks.

Memory implementation notes
=============================

The core memory timing is rather finicky and includes a lot of sub-cycles. It is detailed in the core memory manual page 37 onwards. A read or write cycle takes 500ns total (I think, at least). There are several sub-steps 25ns apart.

To over-simplify, the operation is as follows:

For reading:
1. Turn on Y currents
2. Turn on X currents
3. Latch sense amplifier output

Write timing is similar:
1. Turn on Y currents
2. Turn on X currents & inhibit currents
3. Wait

Note that the timing of step 3, especially for reading, cannot depend on system clock: the access time of the cores is a physical thing and doesn't depend on what the operating frequency is. The length of #1 and #2+#3 is rather asymmetrical as well, so we're probably better off de-coupling memory timing from CPU timing.

CPU state
=============

The CPU is build around an ALU. The ALU has a bypass-able output latch, but it's inputs are not latched:
- L_ALU_RESULT

The memory bus outputs (address and data) are also latched. Bus command is direct-driven from the state machine
- L_BUS_A
- L_BUS_D

The system bus input (BUS_D) is not latched and instead is directly written to the target latches (including L_BUS_D, if needed).

Finally there's are latches for the 4 architectural registers.
- L_PC
- L_SP
- L_R0
- L_R1

The current instruction code is latched in:
- L_INST

The following mode flops are also needed:
- INTDIS: set when interrupts are disabled
- INHIBIT: set when interrupts are inhibited (due to a predicate that disabled the following instruction)
- L_ICYCLE: a 3-bit counter (or a 5-bit one-hot counter?) to time the execution phases of an instruction

Data-flow block diagram
=======================


Operation in each cycle
========================

It would be nice for the CPU to be a bit-serial implementation, but this poses two problems:
  1. We would need extremely fast clocks (on the order of 32MHz) to finish a 16-bit operation in 500ns. I have not been able to create a shift-register of that speed. In fact, I have not been able to create a shift register that can go even beyond 10MHz at this point.
  2. We need a lot of shift registers. And shift registers need D-flops, not just latches. This balloons the transistor count to the point where a bit-parallel implementation appears to be cheaper.

That being said, there is are a couple of potential middle-grounds: a bit-serial ALU surrounded by input and output shift-registers, which can be parallel-loaded from an otherwise bit-parallel CPU. One could also consider a block-serial implementation where - say - 2 or 4 bits are processed in one clock cycle.

Either way, the ISA and the timing description below will assume a bit-parallel implementation for now.

Cycle 1:
- open L_BUS_A and set its input to ALU_RESULT
- set BUS_CMD to READ
  note: we don't alter ALU operation and don't update L_PC either in this cycle. This means that the ALU keeps outputting the next PC, so it's OK to keep L_BUS_A latch open for the whole cycle.
- open L_BUS_D
- Load L_INST - open L_INST and on its input mux:
  - if INHIBIT is 1, set 16b0_100_0_011_00_000000 (i.e. OR PC with 0, i.e. NOP)
  - else if INTDIS is 0 and INT is 0 (i.e. there's an enabled and pending interrupt), set 0x0000
  - else mux BUS_D
- open L_ALU_RESULT (this will load the current PC)

Cycle 2:
- close L_BUS_A -> it will maintain the instruction address while the ALU is busy
- open L_PC and set it's input to L_ALU_RESULT
- close L_BUS_D -> now it retains BUS_D
- close L_INST -> now it contains the next instruction (interrupt, NOP or otherwise)
- set BUS_CMD to WRITE
- clear INHIBIT (this can be moved to any subsequent cycle, if needed)
- Calculate sum of index register and immediate:
  - set ALU_B to the sign-extended version of the IMMED field of L_INST
  - set ALU_A to the register selected by the OPB field of L_INST
  - set ALU_CMD to ADD;C=0
- close L_ALU_RESULT

Cycle 3:
- open L_BUS_A and set its input to ALU_RESULT
- set BUS_CMD to READ, if needed or NOP otherwise
  note: we won't alter ALU operation in this cycle, so the ALU keeps outputting the read address, which is to say that it's fine to keep L_BUS_A open for the whole cycle
- open L_BUS_D and set its input to BUS_D

Cycle 4:
- close L_BUS_D -> now it contains the operand data
- close L_BUS_A -> now it contains the operand address
- Execute instruction:
  - set ALU_B to BUS_D or BUS_A, depending on addressing mode
  - set ALU_A to OPA-selected register or 0. OPA is of course the appropriate field of L_INST
  - set ALU_CMD based on OPCODE or 'OR' if we won't write data (i.e. we get the original data out)
- set BUS_CMD to WRITE - NOTE: here we unconditionally write back our input result. If the target was memory, we will do a second write in cycle 5.
- open L_ALU_RESULT

Cycle 5:
- close L_ALU_RESULT
- Write back result into CPU state:
  - open target register - if any - and set its input to L_ALU_RESULT.
  - set INHIBIT, if needed
  - flip INTDIS, if needed
- Increment PC:
  - set ALU_A to L_PC
  - set ALU_B to 0
  - set ALU_CMD to ADD
    - set carry-in to 1 if PC is not the target register, otherwise set it to 0
- Write back result into memory:
  - open L_BUS_D and set its input to L_ALU_RESULT, if required based on INST
  - set BUS_CMD to WRITE, if needed or NOP otherwise

Here we set up pretty long logical chains:
- Get through L_INST
- Get through the ALU input MUX (from a register)
- Get through the ALU
- Get through the output MUX
All this in a single cycle; granted that cycle is now 500ns.

I think this wavedrom script captures what's going on relatively well:

{signal: [
  {name: 'phase', wave:'4333338', data: [4,0,1,2,3,4,0]},
  {name: 'clk', wave: 'p......'},
  {name: 'BUS_CMD', wave: '6555557', data: ['write','read', 'write', 'read', 'write', 'write', 'read']},
  {name: 'L_BUS_A_ld',      wave: '01010.1'},
  {name: 'L_BUS_A', wave: '65.5..7', data: ['OP--', 'PC', 'opb_result', 'PC+1']},
  {name: 'L_BUS_D_ld',      wave: '1.0101.'},
  {name: 'BUS_D_in', wave: 'x5x5x.', data: ['INST', 'data'], phase: -1.5},
  {name: 'L_BUS_D', wave: '6x5x55x', data: ['op_result--','INST', 'data', 'op_result']},
  {},
  {name: 'L_INST_ld',       wave: '010...1'},
  {name: 'L_INST', wave: '6x5...x', data: ['INST--', 'INST']},
  {},
  {name: 'ALU_A', wave: '6.5.55.', data: [ 'PC-1', 'reg[OPB]', 'reg[OPA]', 'PC']},
  {name: 'ALU_B', wave: '6.5.55.', data: ['0', 'IMM', 'data??', '0']},
  {name: 'ALU_CMD', wave: '6.5.55.', data: ['INC/NOP--', 'ADD', 'OPCODE', 'INC/NOP']},
  {name: 'phase', wave:'4333338', data: [4,0,1,2,3,4,0]},
  {name: 'ALU_RESULT', wave: '5.5.57', data: ['PC', 'opb_result', 'op_result', 'PC+1'], phase: -1.5},
  {name: 'L_ALU_RESULT_ld', wave: '010.10.'},
  {name: 'L_ALU_RESULT', wave: '6x5.x5.', data: ['op_result--','PC', 'op_result']},
  {},
  {name: 'L_PC_ld',         wave: '0.10...'},
  {name: 'L_PC', wave: '6.5....', data: ['PC-1', 'PC']},
  {},
  {name: 'L_<target_reg>_ld', wave: '0....10'},
],
config: { hscale: 2 }
}

