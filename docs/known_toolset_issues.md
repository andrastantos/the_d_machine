# Known toolset issues

Known problems in the TDM toolset (GCC, binutils, GDB, newlib) that are not fixed, with what triggers them and why they're left as they are. The TDM-specific conventions they refer to are in [isa/isa.md](../isa/isa.md).

## GCC

### Jumping out of a VLA size expression restores $sp from an undefined value

- **Test:** `gcc.dg/pr97986-1.c` (execution test fails, exit status 134)
- **Affects:** -O0 only; the test passes at -O1 and -O2
- **Trigger:** a non-local `goto` from a nested function (a GNU extension) called while a variable-length array's size is computed, to a label inside the array's scope
- **Cause:** a generic GCC bug; it only shows on TDM

A variable-length array (VLA) is a local array whose size is only known at run time, such as `int a[n];`. GCC saves $sp at the start of the VLA's block (`__builtin_stack_save`), allocates the array by moving $sp down at run time, and restores the saved $sp when the block is left (`__builtin_stack_restore`).

The test declares `c` with the type `typeof (va_arg (ap, int[(h (), n)]))`, so computing `c`'s size calls the nested function `h`, which jumps back into the enclosing function with `goto d`, to a label after `c`'s declaration:

```
saved_stack.13 = __builtin_stack_save ();   // skipped: h () jumps from before it
...
c.12 = __builtin_alloca_with_align (...);
d:                                          // h () lands here
return n;
finally: __builtin_stack_restore (saved_stack.13);
```

The jump skips the `stack_save`, but the matching restore still runs on the way out, so $sp is loaded from an uninitialized stack slot. The restore of the enclosing block, from a properly saved value, follows immediately and sets $sp right again.

On x86 nothing uses %rsp between the two restores (locals are addressed from %rbp), so the test passes by luck. On TDM, only $r0 can be a pointer base, so every access to a local through the frame pointer ($mr6) first saves $r0 in [$sp], and setting $sp itself goes through the scratch word [$sp-1] (see [The stack scratch word and interrupts](../isa/isa.md#the-stack-scratch-word-and-interrupts)). Between the two restores the code writes to wherever the undefined $sp points:

```
mov  $sp, [$sp-1]        ; $sp = uninitialized saved_stack.13
mov  $r1, $sp
add  $r1, $sp
mov  [$sp], $r0          ; writes to wherever the bad $sp points
mov  $r0, $mr6
mov  [$r0+20], $r1
mov  $r0, [$sp]
...                      ; the next restore fixes $sp, too late
```

That corrupts memory at an arbitrary address, and the program aborts.

**Why it's not fixed:** the bug is in GCC's front end, which lets a jump skip the `stack_save` while still running the matching restore. ISO C forbids jumping into the scope of an identifier with a variably modified type, but GCC doesn't diagnose a non-local `goto` from a nested function that does. TDM's code generation is correct for the code it's given. Making it survive an undefined $sp would mean not using [$sp] and [$sp-1] as scratch, which compiled code relies on throughout. The trigger is a GNU extension used in a way no real program needs, and only at -O0.
