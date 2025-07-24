Introduction
=============

I have written up a bunch of words, complete chapters in fact on how the current sources and the various switches inside my core memory implementation are going to work. I was almost done with all the design when I hit a bump - namely that the compensation network was highly temperature-dependent which is no good - started to poke around and ended up throwing almost everything out, starting from scratch.

That happens, it's called a learning experience. At any rate, if you happen to come across these pages before, you please try to expunge all that information from your memory and I'm terribly sorry to entertain you wil false information.

So, second time, a charm...

A (very) short intro into core memories
========================================

Core memories use ferrite rings (cores) to store information as permanent magnetization. They are magnetized in one direction for a '1' and in another for a '0'. This magnetization is achieved by having wire windings on these cores and sending currents through said windings. This current builds a magnetic field that flips the permanent magnetization of the core.

Readout is achieved in a similar manner: enough current is passed through some windings to cause the magnetic field of the core to align on a particular direction. If it was in the other, it will release its stored energy in the form of an induced voltage spike on a read-out (sense) winding. If it was in the same magnetization, nothing really happens and the core induces no pulse in the sense winding.

For this to work, the core needs to have a "square" hysteresis curve, in other words, it needs to be a pretty good permanent magnet.

These windings that I was talking about are the simplest possible: a wire threaded through the hole in the core. They are single-turn windings. For this reason, they are not really called windings, just wires.

The square hysteresis curve allows for a trick in addressing: instead of using just one wire to send the read or write current through, we use two: an X and a Y wire and we organize the cores into a square matrix. Each of the X and Y currents only carry half of the current (called half-current) needed to flip the magnetization of the cores. Since X and Y wires intersect only on a single core (more on this later), only one core will see this full current applied. A full row and a full column will see half the current, but that doesn't change (much) the magnetization of the core due to the square hysteresis curve.

So, we can select a single core by directing half-currents to one each of the many X and Y wires. Cool.

We read the memory by sending half-currents in one direction through the X and Y wires. These set the magnetic field of the selected core to '0' and induce a voltage spike (about 40mV) on the sense wire, if it wasn't '0' already.

Write is achieved by applying a half-currents in the opposite direction through the X and Y wires, flipping the core in the intersection to the '1' state. Of course, if we try to write a '0' we can simply not do anything. As you saw in the previous sentence, reads are destructive: they clear the bits to '0'. So if we precede every write with a read, we can simply write '1' if needed and nothing if we're fine with the '0' content the read left behind.

Things get more complicated in multi-bit memories: these have one such matrix for each bit-plane, but their X and Y wires are connected in series. This suddenly means that any X and Y wire has (in a 16-bit memory) 16 intersection points. That is fine for reads: we just need individual sense wires for each bit-plane, but what about writes? How do we prevent all selected bits in the bit-planes to flip to '1'? THe answer is an 'inhibit' current. This is sent in the sense wire (at least in my memory) in the opposite direction of the write current. It's amplitude is also a half-current and it cancels out one of the select currents; lowering the total to below the flip current threshold for the given bit-plane.

In essence:

1. We need a way to drive a 'half-current' into any of the X wires (128 in my case) in either direction for reads and writes
2. We need a way to drive a 'half-current' into any of the Y wires (128 in my case) in either direction for reads and writes
3. We need a way to drive a 'half-current' into any of the sense/inhibit wires (16 in my case) in one particular direction during writes

For the topic at hand, we need current sources that can source this magical 'half-current'. This is documented to be 410mA for memory have.Life isn't that simple though. Ever. Among the many complications is that the 'half-current' is temperature dependent.

.... insert text from old chapter ....


Current sources
================

Let's look at how to build a current source now! For starters, this is what DEC did:

.... add picture of current source schematic ....

There are two problems with this circuit. The first is that it uses an op-amp, which I can't use. Because I swore off of integrated circuits in this design. The second is that this is not the whole circuit. It's just a reference current source, the actual half-currents are generated through saturating transformers and more transistors. The use of saturating transformers allow them to turn current sources on and off by driving the transformer cores into (off) or out of (on) saturation. This setup is strange and fabulous and foreign and impossible to replicate.

So what else is out there? There are current mirrors of course:

... add picture of current mirror ....

These depend on - strangely - a voltage source to get a reference current going, then use that to mirror it to the other side. This is the circuit I started off with. As a reference, I've used the same 6.2V Zenner that DEC chose (well, not the same part, but the same voltage), because that is the most stable over temperature. R3 limits the current through the Zenner to a reasonable value. Q9 and Q8 form the current mirror, however if you are not familiar with these circuits, it might be better to think about them this way:

... add picture of the way I drew it, with Q1, Q7 Q9 RT missing ....

In this setup, you see Q8 creating an emitter follower. So it's base and emitter voltage are (roughly) the same. Since the base is 6.2V below VCC, so will its emitter be. This voltage is dropped on a voltage divider, creating a constant voltage source, one where the output voltage (referenced to VCC) can be adjusted by the resistor divider.

Now, I was laying when I said the base and emitter voltages are the same. They are not, and most importantly their difference (Vbe) changes with temperature. This needs to be compensated for, by adding a diode with the same temperature characteristics in series with the Zenner:

... new image with a diode ...

This is easiest to do with using the same (kind of) transistor as Q8, but connecting it's base and collector together, making it into a diode:

... now the full picture ...

And now you see the current mirror re-appearing. Really, it's just an adjustable, temperature-compensated voltage source. Names are confusing sometime...

There are two problems with this voltage source: it can't really source any current; it can only drive a very high impedance circuit. The other problem is that I need a current source, not a voltage one.

The first problem can be solved by a second emitter-follower stage and similar temperature-compensation then the first one. A second current mirror, if you whish. The output of this current mirror is now a high-current, adjustable (VCC-referenced) voltage source.

This voltage source can be used as the base voltage of a common-collector stage:

... add image of just the TIP42C ...

What happens here is that the voltage source on the base will start opening up the transistor until enough voltage is dropped on the sense resistor that it's emitter is one Vbe above the base voltage. If the base voltage is constant, so is it's emitter voltage (again, all referenced to VCC). If that voltage is constant, that means a constant current through the sense resistor. This current (ignoring the base-current for now) flows out on the collector towards the load. So, we finally have a voltage-controlled current source. We just have to hook it up to our voltage reference and we're done. Right?

Well, not quite. There are two more things to take care of: the first is the same temperature compensation trick that all the current mirrors use, but this time for the power transistor. I've placed it into the reference divider circuit, that seemed to be the most convenient place.

... Add full current source schematic here ...

The second is to deal with the the situation when there is no load on the current source. What happens in that case is that Q4, the power transistor does it's best to drop enough voltage on the sense resistor, but fails. It opens up as much as it can, goes to saturation, but still nothing. Now, when the load appears (because we want to do a read or a write), Q4 would need to very quickly start regulating the current. However, it can't; it has to wait for all its minority carriers to vacate the base, in other words, recover from saturation. That takes a long time and results in an unacceptable current spike on the load. To prevent this from happening, I've added D2, a diode, which acts as an artificial load if you wish: while it doesn't draw enough current to stabilize the source, it prevents Q4 from going into saturation. To limit the current flowing through this diode, I've added the base resistor (R4) on Q5. This in turn limits the current through Q5, thus through D2.

OK, we're almost there. The last thing to explain is the temperature compensation: RT is the thermistor that DEC mounted on the memory board. It measures the temperature of the cores. R7 and R13 are there (similarly to what DEC did) to control how much the thermistor is allowed to change the current of the current source. One roughly acts as the offset, the other as the slope setting. Finally, the voltage divider is completed by R1, which can be used to set the current. There is some interaction between R1, R7 and R13, normally all three values would need to be touched for every desired current setting, but it's not that difficult to tune them.

Static behavior
=========================

Let's look at the performance of this source over temperature (this time with RT, the thermistor replaced by a constant resistor):

.... add picture of static behavior

This is not bad at all, the current stays about 1% within the expected range for temperatures between 0 and 50C, the temperature range DEC specified for the core. It of course works from -25 to 125, but with some loss of precision.

Now, lets look at the effect of supply voltage:

... add picture of VCC variation

This isn't bad either. Every volt of change in VCC results in ~2mA of change in current. While VCC is going to be imperfect, still it is a regulated supply, it should be within +/-5% (Which is 1V for a 20V supply). What's more important, maybe, is that I can experiment with different voltage supplies (19.45V laptop adapters or 24V supplies for instance) and not expecting large variation in the output current.

Finally, let's look at how closely I can match the temperature response of the DEC current source:

... add picture of full transfer function

Again, pretty good match both at the 0, 25 and 50C set-points.

Overall, I think this is a pretty decent design, should work for what I need it to do.

Dynamic behavior
==================

Before we get all that smug and satisfied though, let's look at how the current source can regulate load steps!

... add picture of load tester

This brings up the question of what the load looks like: is it resistive? Inductive? Capacitive? The short answer is: I don't know. I tried to measure it, I have two impedance meters at home, neither terribly high fidelity. They both claimed it to be resistive. This seems to backed up by the fact that DEC didn't include any provisions to deal with reactive voltages from an inductive load. At the same time, everything I've read indicates that these memories are complex loads, behave more like a transmission line than a lumped element circuit and can do all sorts of nasty things. Worse: since the cores have many wires threaded through them (the X and Y select wires plus the sense-inhibit wire), they act as transformers. These transformers couple in all sorts of interesting ways to one another. I have some reason to believe that the net result of these transformer couplings is to largely cancel the inductive part of the load out, but I have no idea about the capacitive part. Or the transmission-line effects. For now, I'm going to use a resistive load, because that's the one that I have at least some empirical results for: I can measure their resistance. They are the following

.... add list of line resistances

Finally, the switches are not ideal either. I have a whole chapter coming up on them, but the &TLDR; of it is that they are MOSFETs and diodes. They add their own transient behaviors and capacitances. 

OK, show-time: this is the transient response of the current source

... add picture of load transient ...

This transient can be tuned, if needed by adding a parallel capacitance and/or a series inductance to the sense resistor, which is something I'll do once I have the switches in place. Even then, I probably will have to redo that work in real HW, once I have the true load hooked up; as I said, I don't how the load will act.

Multiple sources
=================

I need not one, but three current sources: one for the X and Y lines each and a third one for the inhibit circuitry. The first two are nominally set to 410mA, the third one to 370mA by DEC. Don't ask why the inhibit current is lower. In theory, all should be the same value, the half-current. It might have to do with the transient behavior of their switches, it might be some detail that I haven't grasped about core memory operation. At any rate, I will faithfully replicate this circuit, or at the very least the ability to replicate it. The simplest way to make these three current sources of course is to replace the whole circuit three times. That works with one problem: DEC only provided a single thermistor on the board. I either have to jerry-rig two more in, or go the other way and make a multi-output current source:

... add picture of multi-output variant ...

There really isn't much to see here, I simply replicated the second emitter follower and the power stage. The sense resistors are selected such that the X and Y sources generate 410mA while the inhibit sources 370mA at room temperature.

At some point I'll have to explain why I need two inhibit sources, but I'll leave that to when I describe the inhibit drive circuit. For now, let's just take that as a given.

Cross-talk
===========

One problem we can have in this setup is if one load influences the current on another. So, let's test that!

... add schematic of crosstalk test ...

Here, I can switch the loads on and off on any of the outputs and by driving the right wave-form, I can examine their effect on the other outputs:

... add some pictures of cross-talk results ....

Summary
=========

I think I spilled enough digital ink on this subject, so let me stop here. This current source design seems to pass muster and hopefully will be useable as the basis for my core memory circuit. It is stable under temperature and supply voltage changes, has multiple outputs with reasonable cross-talk, can adjust the output currents based on the measured memory matrix temperature and seems to have decent load-step-response, at least with resistive loads.

Next time around, I'll discuss what the loads on these sources actually look like.









