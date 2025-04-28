
TTL version
============

How much faster could this machine be if we let go of the core memory idea and use more traditional SRAM (and NOR FLASH) access cycles?

Operation in each cycle
------------------------

Cycle 1:
- write ALU_RESULT into REG_PC
- write ALU_RESULT to REG_BUS_A
- write READ into REG_BUS_CMD

Cycle 2:
- Load the REG_INST:
  - if INHIBIT is 1, load 16b0_100_0_011_00_000000 (i.e. OR PC with 0, i.e. NOP)
  - else if INTDIS is 0 and INT is 0 (i.e. there's an enabled and pending interrupt), load 0x0000
  - else write BUS_D into INST
- clear INHIBIT (this can be moved to any subsequent cycle, if needed)
- write NOP into REG_BUS_CMD

Cycle 3:
- Calculate sum of index register and immediate:
  - write REG_INST IMMED field into REG_ALU_B
  - write REG_INST OPB-selected value into REG_ALU_A
  - write ADD;C=0 into REG_ALU_CMD

Cycle 4:
- write ALU_RESULT into REG_BUS_A
- write READ into REG_BUS_CMD, if needed

Cycle 5:
- Write BUS_D into REG_BUS_D
- Execute instruction:
  - write BUS_D or BUS_A into REG_ALU_B, depending on addressing mode
  - write register content or 0 into REG_ALU_A, depending on OPA field of INST
  - write REG_ALU_CMD based on OPCODE or 'OR' if we won't write data (i.e. we get the original data out)
- write NOP into REG_BUS_CMD

Cycle 6:
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
  - write WRITE into BUS_CMD, if needed

So, we can shave off 2 cycles. This is because we do 2 reads and 1 write per instruction and each read takes 2 cycles. So we waste only 1.
We could assume that reads can be pipelined (fair assumption), so the two reads only take 3 cycles, the one write would be the 4th. This would however require us to be able to get through the ALU in the same cycle when the read response comes back.

Now, if we assume a gate delay (74AHC86 XOR gate, 5V, 50ps load) to be 11ns, we can get through the ALU carry chain in 16\*2\*11 = 352ns. That already is a mere 3MHz clock rate and appears to be the limiter of speed (as opposed to memory). So it seems we want a faster adder. Using the 74HC283 4-bit full adder, one gets 4\*60=240ns speed. So, about 4MHz. Note: this is HC logic, LS apparently is somewhat faster. Note too, that the speed is highly load-dependent, at 15pF load, one would expect another 2x boost in speed.

OK, so assuming that we don't load Cout down, we use these fast adders, we could get to about 125ns delay to get through the ALU. Since memory access times were back then at around 250ns, maybe a 4MHz cycle time is not out of question.

Option 1 would have been to do 6 cycles at 4MHz or 4 cycles at (1/(250+125ns)) 2.6MHz. These are exactly the same performance metrics (0.66MIPS) so, it's not worth the trouble, even if it was possible. Especially because at that point we're much more at the whims of the memory subsystem.

This is compared with the target of about 2MHz clock speed for the transistor based system (whether that's achievable with a ripple-carry adder is to be seen), it would be a 2.6x increase in performance.