ISA overview
============

This is a two-address ISA. One of the operands is a memory location or immediate, the other is a register.
The instruction set allows for read-modify-write of either (or both) operands.

NOTE: read-modify-write for core memories is practically free due to the destructive nature of reads. The memory controller doesn't do automatic write-backs (to save a data-register) so the CPU needs to make sure it happens.

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
- 3b000 - MEM[ IMMED+PC ]
- 3b001 - MEM[ IMMED+SP ]
- 3b010 - MEM[ IMMED+R0 ]
- 3b011 - MEM[ IMMED ]
- 3b100 - IMMED+PC
- 3b101 - IMMED+SP
- 3b110 - IMMED+R0
- 3b111 - IMMED

BINARY group
============

```
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
| 0 |    B_OP   | D |    OPB    |  OPA  |         IMMED         |
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
```

B_OP codes:
- 3b000 - SWAP <-- this one is weird as it writes both operands
- 3b001 - OR
- 3b010 - AND
- 3b011 - XOR
- 3b100 - ???
- 3b101 - ADD
- 3b110 - SUB
- 3b111 - ISUB <-- this is inverse sub, i.e. B-A as opposed to A-B

NOTE: SWAP is special in several ways:
- It writes both operands. This means that the 'D' bit is meaningless and can be re-purposed as follows:
  - If 'D' is set to 0, the INTDIS bit is also flipped during execution.
  - If 'D' is set to 1, normal SWAP operation is performed.
- If one of the targets is $PC, it's value is incremented during the swap operation. So for instance SWAP $PC, $R0 is executed with at location 0x1000, $R0 will contain the value $1001 after the instruction finished.
- SWAP between registers is difficult (as it would need to check for the immediate field being 0), so it is not supported.

D codes:
- 1b0 - reg is destination
- 1b1 - memory is destination

Certain operations, such as NOT (XOR with -1) or NEG (0-A) can only be done with register destinations. To implement memory targets, the instruction would need to be surrounded by a pair of SWAPs to get the arguments in their right location.

UNARY group
============

```
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
| 1 | 0 | U_OP  | D |    OPB    |  OPA  |         IMMED         |
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
```

U_OP codes:
- 2b00 - MOV
- 2b01 - ISTAT <-- stores INT in bit0, INTDIS in bit1
- 2b10 - ROR
- 2b11 - ROL

D codes:
- 1b0 - reg destination; source as well for ROL/ROR
- 1b1 - memory destination; source as well for ROL/ROR

PREDICATE group
===============

```
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
| 1 | 1 |    P_OP   |    OPB    |  OPA  |         IMMED         |
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
```

in this case, we do all operations as if we were doing a SUB and see what the result would be

P_OP codes:
- 3b000 - ==0
- 3b001 - !=0
- 3b010 - <0  (unsigned)
- 3b011 - >=0 (unsigned)
- 3b100 - <0  (signed)
- 3b101 - >=0 (signed)
- 3b110 - <=0 (signed)
- 3b111 - >0  (signed)

These instructions test the condition and if it is satisfied, set INHIBIT bit. This bit disables interrupts for the next instruction as well as force that instruction to be replaced by a NOP. This allows any instruction to be conditional.

Interrupts and reset
-----------------------

- When an interrupt happens, PC is swapped with the content of address 1. The encoding is such that this is instruction 0x0001.

  Simply put, when an interrupt happens, the INST register is forced to 1 cycle 3. Because of this, the saved PC points to the instruction that needs to be retried once the interrupt handler returns.

  Any SWAP with the 'D' bit cleared also inverts INTDIS. This facilitates return from interrupt operations: in an atomic operation, we restore the execution to where it got interrupted while also enabling interrupts. Interrupts are immediately enabled, so if there's a pending interrupt, no forward progress is made. This is a minor price to pay for simplicity.

- reset is done the same way as interrupts, except that address 0 is used. In other words, on reset, INST is forced to 0x0000 and ICYCLE is forced to 2.

- one can enable/disable interrupts by storing the subsequent location of execution in some convenient low address (something that an IMMED field can address), then performing the requisite SWAP operation (with the D bit cleared). By convention MEM[ 2 ] is used for this purpose.

- The interrupt status as well as the INTDIS bit can be checked by the INT_STAT unary operation.

Pseudo instructions
---------------------

NOP:
- this can be achieved by for example XOR-ing a register with an immediate value of 0.


High level language support
-------------------------------

This is the calling convention the toolchain (GDB's unwinder in particular) assumes.

Stack:
- The stack grows down. SP points to the first free location: a push is a store to [$sp] followed by `sub $sp, 1`.

Calls:
- The caller stores the address of the callee in the free location and swaps it with PC. This jumps to the callee and leaves the return address (the address of the SWAP plus one) in the same location:

  ```
      mov  $r1, [$pc + (lit_f - .)]   ; the address of f
      mov  [$sp], $r1
      swap $pc, [$sp]                 ; call f; [$sp] = return address
      ...
  lit_f: .word f
  ```

- The callee allocates its frame below the return address with `sub $sp, N`. The return address is then at [$sp+N], locals at [$sp+1]..[$sp+N-1]; [$sp] is free, ready for the next call. A function that needs no frame (a leaf without locals) skips this.
- To return, the callee frees its frame, then loads PC from the return address:

  ```
      add  $sp, N
      mov  $pc, [$sp]
  ```

Arguments and return values:
- The first argument is passed in R0 if it fits in a word. Further arguments are pushed by the caller before the call, so the callee finds them above its return address ([$sp+N+1], [$sp+N+2], ... after its prologue). The caller removes them after the call returns.
- A first argument wider than a word (a `long`, a struct) goes on the stack instead, and so do all the arguments after it: R0 is then not used. Unnamed (`...`) arguments always go on the stack; the named arguments of a variadic function follow the same rules as in any other call (the format string of `printf` is in R0).
- Multi-word arguments are stored low word first (at the lower address).
- Results of up to 16 bits are returned in R0, 32-bit results in R1:R0 (low word in R0).
- A struct or union is returned the same way if it is one octet long, or two or four octets long and word aligned (it has a member of a type of a word or more, such as an `int`, a `long` or a pointer). Others, such as a struct of two to four `char`s, and results larger than 32 bits (`long long`, `double`) are returned in memory: the caller passes the address of the result as a hidden first argument in R0, and the real arguments all go on the stack. The callee returns that address in R0 (a byte pointer, as for any C data pointer).

Registers:
- R0 and R1 are caller saved: a call may change them.
- SP is preserved: on return it has the same value as before the call.
- The memory registers (see below) follow their own caller/callee saved split.

Example: `int main(int a)` with one local, calling `add2(a, 7)`:

```
main:   sub  $sp, 2                   ; frame: return address at [$sp+2]
        mov  [$sp+1], $r0             ; the local
        mov  $r1, 7
        mov  [$sp], $r1               ; push the second argument
        sub  $sp, 1
        mov  $r1, [$pc + (lit_add2 - .)]
        mov  [$sp], $r1
        swap $pc, [$sp]               ; add2(a, 7), first argument in R0
        add  $sp, 1                   ; pop the argument
        add  $sp, 2                   ; free the frame
        mov  $pc, [$sp]               ; return, result in R0
lit_add2: .word add2
```

Debuggers unwind a frame from the location holding its return address (the caller's SP at the time of the call): the caller's PC is the value stored there, the caller's SP is its address. Within a function, the SP adjustments between the start of the function and the current PC tell how far SP is below that location.

### Memory registers

Memory locations 0 to 31 can be reached by every instruction through its immediate field, so the toolchain treats them as 32 extra registers, $mr0 to $mr31 (`$mrN` is the same as `[N]`). The C ABI divides them up as:

| Registers   | Use                                                                 |
|-------------|---------------------------------------------------------------------|
| $mr0-$mr2   | hardware: reset vector, interrupt vector, scratch for enabling/disabling interrupts |
| $mr3-$mr5   | constants 0x00ff, 0xff00 and 0x7fff, set up by crt0 and never changed |
| $mr6        | frame pointer in functions that need one; otherwise callee saved    |
| $mr7-$mr18  | caller saved ($mr18 also holds the static chain of nested functions) |
| $mr19-$mr31 | callee saved                                                        |

- Compiled code never writes $mr0-$mr5 in the default (supervisor) mode.
- Functions that move SP by a run time amount (`alloca`, variable-sized arrays) or that are the target of a nonlocal goto (`__builtin_setjmp`) keep a frame pointer in $mr6. After saving the callee saved registers the prologue copies SP to $mr6, so like SP it holds a word address, and the frame is addressed from it. The epilogue restores SP from $mr6. Other functions may use $mr6 as an ordinary callee saved register.
- Code compiled with `-muser-mode` runs in user mode, behind the MMU. There locations 0-2 have no hardware role (the vectors and the interrupt enable scratch belong to the supervisor), so the compiler uses $mr0-$mr2 as further caller saved registers. `-muser-mode` is a separate multilib, and `__TDM_USER_MODE__` is defined for it.

### C data types

C uses 8-bit `char`s, even though memory is addressed in 16-bit words:

| Type                        | Size     | Alignment |
|-----------------------------|----------|-----------|
| `char` (unsigned by default)| 8 bits   | 8 bits; a word for whole objects (see below) |
| `short`, `int`              | 16 bits  | 16 bits   |
| `long`                      | 32 bits  | 16 bits   |
| `long long`                 | 64 bits  | 16 bits   |
| data pointer, `size_t`      | 16 bits  | 16 bits   |
| function pointer            | 16 bits  | 16 bits   |

- Multi-word values are stored low word first. Within a word, the low octet comes first.
- Every object, `char` objects included (globals, statics, locals, string literals), starts on a word boundary. This is an ABI rule, not just a code generation choice: code may rely on it when accessing `char` objects.
- Inside arrays and structs, `char`s are packed two per word. `char a[5]` takes 3 words; in `struct { char c, d; int i; }` `c` and `d` share the first word.
- The assembler supports this with `.octet` (one octet; consecutive `.octet`s pack into words, low octet first) and with strings, which are packed two characters per word.

### Byte pointers

Data pointers are byte addresses in "LSB" form: the address of an octet is twice the address of the word holding it, plus 1 for its high octet (bits 15:8), plus 0 for its low octet (bits 7:0).

- A data pointer to word address W is 2*W. To access memory through it, the code shifts it right by 1 (`ror`) and uses the result as a word address. Pointer arithmetic is ordinary integer arithmetic.
- Because pointers are 16 bits, C data must live in the first 32K words of memory (word addresses 0x0000-0x7fff).
- Code addresses (function pointers, return addresses, labels) are plain word addresses and can be anywhere in the 64K word address space.
- The SP holds a word address. The compiler converts between it and byte pointers when it takes the address of a stack object.
- In assembly, `%bptr(sym)` gives the byte pointer of a symbol (2 * its word address); the linker resolves it with its own relocation (R_TDM_BYTEPTR16). For example `.word %bptr(arr) + 4` initializes a pointer to `arr[2]` of an `int` array.

### The stack scratch word and interrupts

Compiled code uses the word just below the stack pointer, [$sp-1], as scratch space: many C operations expand into instruction sequences that free up R1 by saving it there and restoring it afterwards. [$sp] can also hold live data at any moment, for example between storing a callee address and the SWAP that calls it, or between storing an argument and the `sub $sp, 1` that pushes it.

Interrupt handlers (and anything else that can interrupt compiled code on its stack) must therefore leave both [$sp] and [$sp-1] of the interrupted code untouched. A handler that uses the interrupted stack should first move SP down past them:

```
isr:    sub  $sp, 2                   ; skip [$sp] and [$sp-1] of the interrupted code
        mov  [$sp], $r0               ; now safe to save registers
        ...
```

and add 2 back before returning. A handler with its own stack is not affected.

### Literal pools

An instruction's immediate only holds -32..31, so compiled code loads wider values (constants, addresses of data and functions, far branch targets) from a word in the code, PC-relative: `mov $r1, [$pc+(.Llit5-.)]`. These words are collected in literal pools inside each function, each word within -32..31 words of the instructions that use it:

- A pool goes where execution doesn't fall through: after an unconditional jump or a return. Where none is in reach, the compiler puts one in the middle of the code with a jump over it, `mov $pc, $pc+N` (N is the number of words plus 1).
- The uses of a value that are in reach of one entry share it.
- A far jump loads its target from a pool: `mov $pc, [$pc+(.Llit7-.)]`. A far conditional branch is the predicate followed by such a jump.
- A value that ends up out of reach of any pool stays next to its use, with a jump over it (`mov $r1, [$pc+2]`, `mov $pc, $pc+2`, `.word value`).

A pool's words are data in the text section: a disassembler shows them as instructions, and the line table may count them in a neighbouring line. Code that isn't compiled (assembly, crt0) needn't use pools; it can load its literals in any of these ways.

Miscellaneous quirks
------------------------

Arbitrary loads/stores/jumps:
- A full 16-bit immediate can be put in the code segment and loaded in a single instruction using PC-relative addressing. The offsets for these locations are a bit small (+/-32 locations), so one might have to jump over such constant sections to not run out of space. These jumps are also PC-relative (i.e. load PC with PC+IMMED), but that doesn't seem to be a big limitation: we could have 32 long immediates bunched up like that but it's unlikely that there are more than 32 instructions *within* 32 locations away from that section that need long immediates. The overhead seems rather minimal: one extra instruction every 32 or so operations is a 3% penalty.

Special addresses:
- Address 0 (MEM[0]) is the reset vector.
- Address 1 (MEM[1]) is the interrupt vector.
- Address 2 is (by convention) used as a scratch-pad register for enabling/disabling interrupts

Input/Output
-------------

I/O is memory mapped. One thing that needs to be contended with is the pernicious read-modify-write behavior of the CPU. This puts some restrictions on how I/O can be designed.

Many peripheral chips are not friendly to this bus behavior. However, we're talking about a transistor computer, so peripherals are by necessity one-off, custom designs. In that case, this quirk of the CPU bus can be accommodated.
