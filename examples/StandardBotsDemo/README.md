# Standard Bots arm + ARTUS hand demo

Drives an ARTUS hand end-effector mounted on a **Standard Bots** robotic arm through a pick-and-place cycle: the arm runs a routine built in the Standard Bots routine editor, and this script watches the routine's step state over the Standard Bots cloud API, grasping/opening the hand at each waypoint.

## Files

- [`standard_bot_example.py`](standard_bot_example.py) — Main demo. Wakes the hand, then polls the arm's routine state and triggers grasp/open at the configured waypoints.
- [`find_routine_id_standard_bot.py`](find_routine_id_standard_bot.py) — Utility script: lists the routines on your robot and their IDs, so you can fill in `routine_id` / `first_target_id` / `second_target_id` below.
- [`standard_bots_config.py`](standard_bots_config.py) — Small YAML loader shared by both scripts.
- [`standard_bots_config.example.yaml`](standard_bots_config.example.yaml) — Config template.

## Setup

1. Install the extra dependency:
   ```bash
   pip install -r examples/StandardBotsDemo/requirements.txt
   ```
2. Copy the config template and fill in your own values — **do not commit the real file**, it holds your API token:
   ```bash
   cp examples/StandardBotsDemo/standard_bots_config.example.yaml examples/StandardBotsDemo/standard_bots_config.yaml
   ```
3. Configure the ARTUS hand as usual in [`examples/config/robot_config.yaml`](../config/robot_config.yaml) (port, robot/hand type, etc.) — this demo uses the same `ArtusConfig` as the other examples.
4. Run `find_routine_id_standard_bot.py` once to get `routine_id` and the two waypoint (target) IDs from your Standard Bots routine editor, and paste them into `standard_bots_config.yaml`.
5. Run `standard_bot_example.py`.

## Mental model

```
[ Standard Bots arm, running a routine ] --cloud API--> [ this script watches current_step_id ]
                                                                    |
                                                                    v
                                                     [ ArtusAPI_V2 grasp/open on the hand ]
```

The hand and the arm are controlled through two completely separate channels — this script does not send anything to the arm, it only reads routine state and reacts by commanding the hand.

## Related reading

- [Examples index](../README.md)
- [`general_example/`](../general_example/) for the base ArtusAPI_V2 flow this demo builds on
