Introduction
=============

I've mentioned in passing that my Disintegrated Computer will use magnetic core memory for storage. That of course means I have to design and build a core memory. Well, almost. I bought a core memory module on eBay that was originally part of a PDP-11. Specifically it is an H-217C module, which is a 32kByte (16kWord x 16 bits) core memory matrix. But just that. Well, almost. There are some diodes on it as well as something, called a precharge circuit.

There is however a lot more to core memory then just the cores. All sorts of interesting drivers and amplifiers and current sources and switches and diode matrices are needed to make it tick. I don't have any of those things and even if I did they would be no good: the PDP-11, being a '70-s era design, uses integrated circuits all over the place. In my design, I decided to go without any of those frills and do everything with transistors.

All this means that I have a mighty design project in front of me, which I will start documenting here as I go. Before I do that however, it's worth spending some time getting familiar with how core memories worked. And let me tell you, they were weird!

A single core
===============

The basic storage element of a core memory is a ferrite ring. Ferrite rings never went out of fashion really, they are still are widely used as EMI suppression devices. However the ones used for core memories are distinct and special: these rings were made of a special ferrite material, something that can be permanently magnetized.

This is the basic idea behind core memory (and really all magnetic storage, including tapes, floppy disks, even hard drives): get a material that can be magnetized, then use an electromagnet (really a coil) to magnetize them

... add picture of a single ring with a coil on it ...

All we need to do is to loop some wire around the ferrite bead, and,  boom, storage! In fact, if we wanted to go simple, we want to loop as little as possible. And as little as possible means that we simply thread a wire through the hole of this magnetic doughnut:

... add picture of core with a wire through it...

Still works, just needs more juice to drive. But how much juice? Well, that's ... complicated. The reason these cores (or any ferromagnetic material) can act as a permanent magnet is that their response to magnetic field contains a hysteresis:

... add picture of hysteresis curve ...

The way you read this is as follows: for any given magnetic flux value (X axis) the core can be in two possible states: these are the two intersections of the curve with a vertical line

... draw vertical line ...

As the flux changes the magnetic field (TODO: is it called flux and field???), the core will respond by 'sliding' on the curve to the left or right, depending on the direction in the change of the field. Notice two important things: if set the external flux to 0, (look at the Y axis intersections with the curve), the core can still be in two distinct places. These correspond to the two possible magnetization states of the core, and this is what we call a permanent magnet: some of the magnetic field is there even if the external field is removed. This is what allows us to use this device for storage: if we have a way to control which of the two states the magnetic field ends up (and read it back of course), we can store and retrieve bits. We just need to designate the 'top' point, magnetized in the 'up' direction as '1' and the 'bottom' point, magnetized 'down' as '0'. Or the other way around, it doesn't really matter as long as we stick to it.

The second point is about control: yo see how this curve is closed. Let's imagine that we start at the 'bottom' point, in the '0' state. Now, let's start increasing the magnetic flux (move the core to the right on the curve). Eventually we slide its state up all the way to the top-right corner, where the two parts of the curve merge. At this point, we've flipped the magnetic state of the core. Actually, the flip happened, when we went through the really steep part of the curve

... add picture highlighting the steep part ...

During this flip, we remove any remnant magnetic field, and it's associated energy. This is going to be important later, so remember it. After the flip however, we're at the to-right corner. Now, let's start decreasing the external magnetic field, sliding the state to the right. The core's state is going remain magnetized in the 'up' direction, so it's going to follow the top part of the curve

... add picture of the direction ...

By the time we completely removed the magnetic filed, the core landed in the '1' state. We successfully flipped its magnetic field.

Of course we can flip it back by applying and removing a sufficiently strong field in the opposite direction.

Before we move on, let's consider three other cases:

First, let's imagine our core in the '1' state and start applying a positive external field (moving again to the right in the diagram). Even if we move all the way to the point where the two parts of the curve meet, we didn't really change anything: the cure stayed in its 'up' magnetized state all the way. There was no flip, there was no energy release and, if we start removing the field, it will return to the '1' position.

Now, let's imagine the same setup. Our core is in the '1' state and we start applying some external field that shifts the state to the right. However, the maximum field strength is much lower then previously, we don't move the core all the way to the intersection point. Just a little bit to the right and back. Of course, in this case, just as before no magnetic flip will happen, the core will return to its '1' state when the field is removed.

Finally let's apply the same weak field to a core, but this time make sure that the core starts in the '0' state. We move it a little to the right, but not all the way to the intersection point, then back. This time the '0' core also didn't flip! It didn't release its energy, it stayed a 'down' one and returned to the '0' position when the field is removed.

All of these are going to be important soon. Before we move on, a few more comments on the shape of these hysteresis curves.

It should be obvious that the reliability and noise immunity of this storage system depends on the size of the opening of this curve: the larger the better. The second point may not be immediately obvious: all of what I've described is really only an approximation and works when the hysteresis curve is largely rectangular. Again, the close, the better. Both of these things are properties of the material the ferrite ring is made of, and these exact properties make these core memory rings special. Don't expect to just order some ferrite rings from Amazon and expect them to work. They wont, unless they were specifically designed for this application.

