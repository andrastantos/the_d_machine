NTSC timing:

From: https://www.technicalaudio.com/pdf/Grass_Valley/Grass_Valley_NTSC_Studio_Timing.pdf and https://pub.smpte.org/pub/st170/st0170-2004_stable2010.pdf

Horizontal blanking: 10.9us +/-0.2us: this includes front-porch, back-porch, color-burst and sync pulse
The line-rate is: 63.5us, this is from sync to sync
The active period is: 52.6us, but can include border
For NTSC there are 485 active lines, a total of 525 lines, with a refresh rate of ~60Hz.
The vertical sync is:
   Field-one:
      3 lines of black (with middle-sync)
      3 lines of v-sync (with inverted sync both in the end and the middle)
      3 lines of black (with middle-sync)
      11 lines of blank (with normal sync)
   Field-two has
      3.5 lines of black (with middle-sync)
      3 lines of v-sync (with inverted sync both in the end and the middle)
      2.5 lines of black (with middle-sync)
      11 lines of blank (with normal sync)
      this ignores that the last line and the first line has only half-line info. I assume black there already

=========================

With a 2MHz clock and 16-bits every 6 clock cycles, one can get a pixel every 0.1875us. This, with an NTSC active period of 52.6us supports 256 active pixels per scan-line and ~280 total pixels per scan line. Of course clock rate will need to be adjusted to align well with timing. At any rate, 256x256 resolution seems doable (262 scan-line per field). This is obviously not 4:3 aspect ratio. To get there, we would need on the order of 320x240 resolution. That corresponds to 48.2us active video or 0.150625us per pixel. That’s 401.6 clock period, or about 2.5MHz and crystal frequency of 9.95850MHz. That’s pretty close to, but not exactly the 9.54545MHz NTSC clock. But maybe my math is incorrect here. At any rate, running at close to 2.5MHz is dicey.



All in all:

2MHz clock -> 256x256(ish) resolution, total memory needed: 8kB (4kW)
2.5MHz clock -> 320x240 resolution, total memory needed: 9.375kB (4.6875kW)

Timing, assuming the 2MHz variant:

    Front-porch: 3 cycles
    HSync: 9.4 cycles
    Back-porch: 9.4 cycles
    Active portion: 105.2 cycles

This is a problem in that we can’t generate the required resolution. We normally would be running from a 4x clock for timing reasons, but that doesn’t work well with video. For video, we would like to see on the order of 5.33333MHz clock. To get both 2MHz and 5.333MHz, we would need a crystal of 16MHz. Maybe 8MHz, if we used both edges?

    5.3333 = 8/1.5
    2 = 8/4

We would also need to synchronize the CPU state-machine to the 5.33MHz clock somehow. This pixel clock rate would come out

Either way, the 5.333MHz clock would come out to:

    Front-porch: 8 cycles
    HSync: 25.066 cycles
    Back-porch: 25.066 cycles
    Active portion: 280.5333 cycles

After rounding, this becomes:

    Front-porch: 8 cycles
    HSync: 25 cycles
    Back-porch: 25 cycles
    Active portion: 280 cycles

Which is 0.666 cycles short over 338 clock cycles. Or, the proper crystal rate would be 7.98425196851965MHz. That delta is 2000ppm, so maybe relevant? Probably no

As far as dividers are considered, we need even more coarse quantization:

    Front-porch: 8 cycles
    HSync: 24 cycles
    Back-porch: 24 cycles
    Front blank: 10 cycles
    Active screen: 256 cycles <<- start counter here
    Back blank: 16 cycles

This will make the active portion more aligned to the left, but all but the total count is divisible by 8.

So, we would have a counter, running from 5.333MHz, running from 0 to 337.  This is a 9-bit counter. The comparisons happen as follows:

    TC comparator for 337 (sync reset)
    Coarse trigger: (bottom 3 bits all 1)
    Top-6-bit comparators:
        31 – end of active
        33 – end of back-blank
        34 – end of front-porch
        37 – end of hsync
        40 – end of back-porch
    For VSync we'll need to add sync pulses in the center of the scan-line as well. These pulses are just as wide as normal syncs (so 3 counts, starting at count 14):
        14 - start of VSync serration
        17 - end of VSync serration

This seems to be large AND gate (31), and a 3-bit decoder with proper enables for all the rest. Some cleverness might be needed for the VSync pulses. We could also reset the horizontal counter in some form during VSync if that's easier.

===========

Now, on to vertical timing:

For NTSC there are 485 active lines, a total of 525 lines, with a refresh rate of ~60Hz.
The vertical sync is:
   Field-one:
      3 lines of black (with middle-sync)
      3 lines of v-sync (with inverted sync both in the end and the middle)
      3 lines of black (with middle-sync)
      11 lines of blank (with normal sync)
   Field-two has
      3.5 lines of black (with middle-sync)
      3 lines of v-sync (with inverted sync both in the end and the middle)
      2.5 lines of black (with middle-sync)
      11 lines of blank (with normal sync)
      this ignores that the last line and the first line has only half-line info. I assume black there already

For 525 scan-lines, one needs a 10-bit counter. Since we have 485 active lines in there, we can't really implement 256 vertical resolution. The ZX spectrum used 192 vertical lines. The 'safe' area is defined as about 200 scan lines. Taking the 200 number for now, here's how it would look like:

- 200 active lines (we start the counter here)
- 31 v-blank
- 3 v-blank with middle-sync
- 3 v-sync with middle-sync
- 3 v-blank with middle-sync
- 11+31 v-blank
- 200 active lines (second field, repeat of first)
- 31 v-blank
- 3.5 v-blank with middle-sync
- 3 v-sync with middle-sync
- 2.5 v-blank with middle-sync
- 11+31 v-blank

We 'tick' the vertical counter every time we get an HSync from the horizontal engine. This means that the serrations are going to count as double scan-lines (and go by twice as fast). With that adjustment we get:

- 200 active lines (we start the counter here)
- 31 v-blank
- 6 v-blank with middle-sync
- 6 v-sync with middle-sync
- 6 v-blank with middle-sync
- 11+31 v-blank
- 200 active lines (second field, repeat of first)
- 31 v-blank
- 7 v-blank with middle-sync
- 3 v-sync with middle-sync
- 5 v-blank with middle-sync
- 11+31 v-blank

We will also do another trick: we have a single-bit field-identifier, which determines if we're in the first or the second field in the above, i.e. the comparison values for two of the timing values (adding and subtracting one each). This allows us to reset the counter for every field and - as a consequence - use the bits form the vertical counter as part of the memory address generation (bottom 7 bits coming from the horizontal counter), so with that:

- 200 active lines (we start the counter here)
- 31 v-blank
- 6 or 7 v-blank with middle-sync
- 6 v-sync with middle-sync
- 6 or 5 v-blank with middle-sync
- 11+31 v-blank

In binary values:

- 0b0_1100_0111 : end of active lines (at count 199 to allow for sync reset)
- 0b0_1110_0110 : end of v-blank
- 0b0_1110_110? : end of v-blank with middle-sync. ? is zero for even, one for odd fields
- 0b0_1111_001? : end of v-sync with middle-sync. ? is zero for even, one for odd fields
- 0b0_1111_1000 : end of v-blank with middle-sync. This is where we re-align, so no ? needed anymore (thank God)
- 0b1_0000_1110 : end of field: reset counter and flip field-bit

We need to decode 6 values, I think it's a custom '74ls139'-style thing, but we can rely on the counter providing both inverted and non-inverted values so, really it's just a bunch of AND gates.

This creates the timing generator.

Video logic
============

The address is generated from bits 7-4 (inclusive) of the horizontal and bits 7-0 of the vertical counters. This is a 12-bit address, so we're mocking around in a 4kWord space. The top 4 address bits are statically generated by a latch (video RAM base address register). Every instruction has 2 cycles worth of time to read-refresh the addressed word from core memory. This is fed into a 16-bit shift-register, which is shifted out during the execution of the instruction (this is why we need weird clock ratios: 6 CPU clock cycles correspond to 16 video clock cycles). The shifted data is AND-ed with the blanking signal and then combined with the porch and sync signals to generate the proper analog video signal. And, well, basically that's it.

Overall, except for the annoyance of the large counters (a 10-bit and a 9-bit one) and a 16-bit shift register, this really isn't that bad.