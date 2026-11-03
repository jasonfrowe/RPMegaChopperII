# RPMegaChopper gameplay: the baseline

How the original *RPMegaChopper* (`../RPMegaChopper/src`) plays, read from
its source, for the systems the sequel copies. Distances are in pixels and
speeds in pixels per frame (60 frames a second). "Landed height" is the
chopper's top when it sits on the ground (`GROUND_Y`); heights are measured
up from there.

Where the sequel departs from this on purpose, the last section says so.

## Hostages (`hostages.c`)

**Coming out.** A prison that has been breached lets one hostage out every
45 frames, at its door, but only while nobody stands within 8 px of the
doorway and a hostage slot is free. There are 16 slots and a hostage keeps
its slot while aboard, so at most 16 are out or aboard at once.

**Waiting.** Out of the prison a hostage walks to a waiting spot near it,
at 0.5 px/frame, and stands there waving.

**Seeing the chopper.** A hostage heads for the chopper's middle when the
chopper is **low** (its top within 64 px of landed height, flying or not)
and within 150 px. Otherwise it goes back to its waiting spot.

**Boarding.** When it arrives (within 8 px of the chopper's middle), it
climbs aboard if the chopper has landed, is within 12 px, and is not
crashing. A low hovering chopper draws a crowd underneath that waits for it
to land.

**Keeping apart.** A walking hostage stops if another stands or walks
within 12 px ahead of it in the direction it is going (hostages waving at
the home base don't count). So they line up instead of piling together.

**Crushing.** Coming down low (top within 14 px of landed height) but not
yet landed, and not holding *up*: any hostage under the chopper's middle,
within 8 px if the chopper faces the screen or 15 px if it faces sideways,
is killed.

**Unloading.** Landed in the home zone, the chopper lets one passenger off
every 30 frames, at its middle. Each runs for the home base door and is
saved the moment it gets there. The **last** one off stops at the door and
waves for 120 frames, then goes in. Only that one waves; the rest go
straight in.

**Animation.** A frame every 7 frames: running frames while walking, and
the two waving frames while standing still. The last one at the door
switches waving frames every 10 frames.

**Lost.** Shot (by the player's cannon, ±5 px wide, ±7 px tall), hit by a
falling tank shell, crushed, or aboard a chopper that goes down.

## Tanks (`tanks.c`, `ebullets.c`, `bomb.c`)

**When.** No tanks at all until 4 hostages are aboard or saved. Then every
prison's garage is filled with 2 tanks.

**Where from.** Only the prison nearest the chopper sends tanks, at most 2
on the map. Every 60 frames at most, it rolls one out from 320 px to the
left of the prison (if none of its tanks is on that side), else 320 px to
the right, but only if that spot is off screen (by 32 px).

**Moving.** 1 px/frame toward the chopper, but never more than 100 px from
its prison; stopped when within 4 px of being under the chopper; and
never within 45 px behind another tank. The turret points up-left, up or
up-right as the chopper is more than 20 px left, within 20 px, or more
than 20 px right.

**Leaving.** When another prison becomes the nearest, a tank goes back into
its own prison's garage (and can come out again later).

**Firing.** Only while on screen. Not for 20 frames after rolling out, and
for 30-60 frames after each shot; otherwise a 2% chance every frame. At most
2 shells in the air. The shell is aimed at a point 32 px above the
chopper's top, and leaves from the tank's middle at one of five angles,
picked from how steep that is:

| | up | steep | diagonal | shallow | low |
|---|---|---|---|---|---|
| speed across | 0 | 2.1 | 4.3 | 5.4 | 6.0 |
| speed up | 6.0 | 5.6 | 4.3 | 2.4 | 0.9 |

Gravity pulls shells down 0.125 px/frame each frame, so the steepest shot
climbs about 144 px and no higher: flying high is safe from tanks. A shell
hits the chopper within 12 px across and 8 px up or down of its middle, and
on its way down, close to the ground, it kills a hostage within 6 px.

**Destroying one.** The cannon does nothing to tanks. Only a bomb, and only
a bomb dropped from **more than 60 px** above landed height: such a bomb
falls to tank depth, where it destroys a tank within 20 px of the tank's
middle. Dropped lower, it bursts on the ground short of the tanks.

**Respawn.** A destroyed tank goes back into its prison's garage, and that
prison waits 300 frames (5 s) before sending another. Tanks never run out.

## Bombs (`bomb.c`)

Facing the screen, *fire* drops a bomb from the chopper's middle. One at a
time; each press drops one. It falls straight down at 3 px/frame (it does
not keep the chopper's speed), and bursts at the depth described above.
Bombs don't hurt hostages and don't open prisons (the cannon does that).

## The fighter jet (`jet.c`)

**When.** No jets until 24 hostages have come out of the prisons, and never
while the chopper is east of the safety line (about halfway between the
last prison and home). One jet at a time.

**Why.** Two timers, counted while no jet is out:
- **On the ground** more than 120 frames (2 s): from then on a 2% chance
  every frame of a **bomber**.
- **High up** (chopper's top within 75 px of the top of the screen) more
  than 240 frames (4 s): from then on a 2% chance every frame of a
  **fighter**.

Both timers reset when the jet comes, when the condition stops, and east of
the safety line.

**The run.** It comes in just off screen from a random side and flies
straight across at **4 px/frame**.
- The **bomber** flies 80 px above landed height. When the chopper is 68 px
  (±10) ahead of the jet's middle it lets go a bomb, which moves on at
  **2 px/frame** across and falls under gravity of **0.125 px/frame** each
  frame, starting from no speed down. It hits the chopper within 10 px of its
  middle, otherwise bursts on the ground.
- The **fighter** flies at the chopper's height. When the chopper is within
  100 px it fires one shot straight ahead at **6 px/frame**, which hits within
  10 px.

After its one attack the jet climbs away at 2 px/frame and is gone once off
screen. The cannon can shoot it down (within 12 px across, 8 px up or down,
of its middle). The jet itself doesn't collide with the chopper.

## The balloon (`balloon.c`)

**When.** One balloon, once 16 hostages have come out of the prisons.

**Appearing.** 64 px off screen to the left or right (a coin toss), but
never east of the safety line (then it tries the left), at 60 px above
landed height.

**Moving.** Toward the chopper's middle, 1 px/frame across and 0.5 up or
down, but never lower than 32 px above landed height, so it can't reach a
landed chopper. East of the safety line it turns back west.

**Hitting.** Touching the chopper (within 18 px both ways, middle to
middle) destroys both. Hit by the cannon (within 10 px across, 18 px up or
down, of its middle), it stops, drops (starting at 1 px/frame, gravity
0.125 px/frame each frame) and blows up on the ground.

**Respawn.** 300 frames (5 s) after it is destroyed, by either.

## Where the sequel departs on purpose

(The turn button working in the air only, and nothing else new about
turning, is the original's rule.)

- **Waiting spots:** the original sends each hostage to one of four spots
  near its prison by slot number, so they still bunch at the door. The
  sequel gives each of the 16 its own spot, 12 px apart on both sides of
  the door, the first ones out going furthest, so they spread along the
  prison and the doorway stays clear.
- **Keeping apart:** a hostage walking straight at another doesn't make it
  stop, so two can't freeze face to face.
- **Bombs open prisons** too, and the cannon still does.
- **Tanks don't twitch:** at the end of its leash a tank stops instead of
  turning back, and once parked under the chopper it stays put until the
  chopper is 12 px off. The turret swings with a little slack too.
- **The safety line is marked** by a border checkpoint with a second flag,
  halfway between the last prison and home.
- **The balloon** is a motorised barrage blimp (32x32) with a mine below
  it, facing the way it moves; its hit boxes are a little wider to match.
- **Tanks keep to their zone:** a prison sends its two tanks only once it
  has been opened and is the nearest, from just out of sight (300 px), on a
  schedule rather than the original's "4 hostages aboard" trigger: the
  first comes into view 8 s after the first prison you open is opened, 6 s
  at the second, 5 s at the third and fourth, the second tank 3 s later.
  Then, unlike the original, its tanks stay out in its zone (the prison
  +-200 px) for good: they patrol it slowly (+-140 px) until the chopper
  comes within 180 px, chase it (firing) but never past the zone's edge,
  and go back to patrolling 120 frames after losing it. So flying home from
  a far prison you pass the tanks of every zone you have opened. Every
  prison's tanks are tracked; only the two nearest the chopper move and
  show, and they swap in and out only out of sight. A destroyed tank goes
  back to its garage after 300 frames, to be rolled out again. They hold
  fire 90 frames after appearing (20 in the original).
- **Tank fire is aimed:** at each shot a tank flies eight launch angles (90
  down to 20 degrees, all one speed) in a quick simulation and takes the
  one that reaches the chopper's height closest to where the chopper will
  be by then, leading its motion (wind and drafts included), give or take
  6 px. Shells climb about 110 px at most, so a chopper with its top above
  about screen row 60 is out of reach, which is inside the jets' zone
  (above row 75): no height is safe from both. They fire more often than
  the original (4% a frame after 24-48 frames' reload, not 2% after 30-59)
  with up to 3 shells in the air.
- **The bomber aims:** it works out how long its bombs take to fall to the
  chopper and how far they carry, and drops a stick of three, 16 px apart,
  centred on where the chopper will be. Each bursts on the ground and takes
  a chopper within 18 px that is on or near the ground. (The original
  dropped one bomb at a fixed lead.) Lifting off at the warning escapes.
- **The balloon** waits for 24 hostages out (not 16) and appears 128 px
  off screen (not 64).
- **Seeing the chopper:** a waiting hostage also comes when the chopper is
  low within 150 px of its own prison's door, not only of itself, so the
  ones waiting furthest out aren't left behind.
- **A longer world:** 4,608 px rather than 4,096, the extra between the
  last prison and home, with the border further east; tanks never roll
  out east of the border.
- **Blizzards** are new: now and then the far scenery whites out, snow
  blows across, and gusts push the chopper sideways and, on another beat,
  up and down.
- **The balloon at the border** backs off 80 px west before coming back,
  so it patrols along the line instead of hanging on it.
- **Jets** wait until the third prison has been opened (not 24 hostages
  out), and they are telegraphed: after 2 s up high a warning to get low;
  when one is coming, "JET INBOUND!" and a reticle blinking for 1.5 s at
  the screen edge it will come from, at the height it will fly (locked
  when it sets off, so dropping away dodges it).
- **Sizes:** the sequel's chopper is 40x20, its tank 40x20, its jet 40x16,
  its balloon 16x32; distances "from the middle" use those.
