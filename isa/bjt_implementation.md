

To get speed, we need schottky transistors. These have a schottky diode across the BC pins, which limits this voltage to about 0.2V, or in other words the V_ce to about 0.5V. This in turn means that the transistor can't enter saturation, thus the Miller effect is defeated and the transistor can be turned off very quickly. There are two down-sides:

1. The current through the schottky diode will have to be sufficiently high to drop ~0.5V on the CE junction. Since at this point the transistor is open, the resistance here is low, thus a high current is needed. This current is coming from the driver (i.e. the thing that drives B), so the input current to the gate is high
2. Since V_ce is 0.5V, the logic level is not clean.

How to make a fast, cheap bit-cell?

1. We need an N-type schottky inverter. This needs to create a clean logic high (through a pull-up) and about 0.5V logic low. We need an emitter-follower input stage to provide the requisite input current. This thing would need to source current, so it also needs to be N-type.
2. We need a complementer P-type equivalent.
3. Cross-connect these two. This should mean that each inverter sees a clean logic level where it needs it and (since this level is provided by the collector-resistor) requires only a small input current to achieve that.
4. We need to rig up some sort of load logic, probably by overriding the emitter-follower stage (somehow) to control writes.

If all of this is successful, we would have a 6T/2D bit-cell. The power consumption would still be through the roof, so lowering Vcc to the absolute minimum is going to be needed.

I don't know the behavior of this over temperature, but I guess that can be tested once the basic circuit is operational.

Given that I need approximately 128 bits of state in the CPU, this would mean ~1000 semiconductors. $0.01 each would come out at $10, that's not the issue, the pick-and-place burden is more impactful.

Still, with a ~100T ALU we have line of sight for a ~2000T CPU and a ~4000T computer.

OK, so quick test: the complementer idea doesn't work at all: the rise times are horrendous. But, the low (with the 0.5V offset) is sufficient to drive the next stage, so the rise-times don't matter all that much. We don't seem to be able to drop VCC below 5V without significant degradation in speed.

Idea: since V_ce is held constant at ~0.5V and since the corresponding current is whatever it is, we can lower Rc to source most of that current. This in turn will lower the current through the diode and thus the drive current from the base, maybe even to the point that the emitter follower is not needed anymore.

Well, that didn't work at all: the diode current stayed constant, all I managed to do was to increase the collector current a bunch. The rise time improved somewhat, but even that wasn't spectacular. V_ce did move by about 50-60mV (which of course is the result of the extra current flowing though the transistor).

If I disconnect the diode, V_ce (even though I_c is much higher, even 100mA) is still much lower. So, the theory I put together above doesn't hold at all. What gives??

At any rate, another revelation: if I drive the input with a voltage source (as opposed to an emitter follower), suddenly both logic levels are perfect. So, let's follow that thread...

A 1K pull-down in the emitter follower output neatly cleaned up the rising edge. Well, neatly is relative: it's still 160ns.

After some tinkering, I managed to get an inverter design that (without load) gets to full-swing output, but with load it can't. It still reaches about 1V swing, and importantly, it can drive 'itself', so a 4T(+4D) bitcell is possible. Rise and fall times are in the 10ns range. Current consumption is on the order of 8mA per inverter, so 16mA per bit. Manageable.

The next step is to figure out an enable/overwrite logic and a read-out logic.

BTW: for whatever reason my fast logic gates stopped being fast. Not sure why. They also started consuming tons of current. So I'll have to go back and redo all that work too.

Temperature dependence is also very minimal.

The DC transfer function is vert 'class B' style with two knees, one at ~0.7 and another at VCC-0.7V. Which gives me an idea: let's lower VCC!

We can lower VCC to 2V and things still work, even over temperature. The power consumption is dropped to about 1.5mA per inverter. So the challenge is: can we make a 2V compatible fast logic gate? If that works out, we can work with this! The swing reduced to 0.4V within the cell and ~1.6V outside. This might mean some noise-immunity issues though lower swing also means less noise...

I actually think I shouldn't go below 2.5V, although things don't fall apart completely even at 1.8V, unless I also allow 125C temperature (which is unrealistic). At any rate, for now, let's stick with 2.5V.

There is one problem with this bit-cell: it's threshold voltage drifts away from the center as VCC changes.

The problem with the old inverter design is shoot-through. Massive, massive shoot-through.