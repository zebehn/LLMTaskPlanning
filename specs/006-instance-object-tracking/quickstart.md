# Quickstart: Instance-Aware Object Tracking

**Feature**: `006-instance-object-tracking`

---

## Scenario 1: Transformation task — heat an egg and place it in fridge

This scenario tests the core fix: the model picks up Egg_1, heats it, then correctly navigates back to Egg_1 (not a different egg) to retrieve it.

### Expected observation trace (after fix)

```
Task: Put a hot egg in the fridge.

Act: find a egg
Obs: Found egg. You are now near the egg on the countertop.

Act: pick up the egg
Obs: Picked up Egg_1.           ← instance label now in observation

Act: find a microwave
Obs: Found microwave. You are now near the microwave.

Act: open the microwave
Obs: You opened the microwave.

Act: put down the egg
Obs: Put Egg_1 in Microwave_1.  ← both labels now in observation

Act: close the microwave
Obs: You closed the microwave.

Act: turn on the microwave
Obs: You turned on the microwave.

Act: turn off the microwave
Obs: You turned off the microwave.

Act: open the microwave
Obs: You opened the microwave.

Act: find Egg_1                 ← model uses instance label to return to same egg
Obs: Found Egg_1. You are now near Egg_1 in the microwave.

Act: pick up the Egg_1
Obs: Picked up Egg_1.

Act: find a fridge
Obs: Found fridge. You are now near the fridge.

Act: open the fridge
Obs: You opened the fridge.

Act: put down the Egg_1
Obs: Put Egg_1 in Fridge_1.

Act: done
```

---

## Scenario 2: Simple place task — no change in behaviour

Instance labels appear but the model does not need to use them for single-object tasks.

```
Task: Put a knife on the countertop.

Act: find a knife
Obs: Found knife. You are now near the knife on the diningtable.

Act: pick up the knife
Obs: Picked up Knife_1.         ← label present but not needed for this task

Act: find a countertop
Obs: Found countertop. You are now near the countertop.

Act: put down the knife
Obs: Put Knife_1 in CounterTop_2.

Act: done
```

---

## Scenario 3: Instance-specific find fails gracefully

```
Act: find Egg_99
Obs: Instance ID 'Egg_99' not found in object registry.
```

The model receives a clear error and can recover by falling back to `find a egg`.
