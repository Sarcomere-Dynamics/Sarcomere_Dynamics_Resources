# Commanding Motion

## Setting Joints

Each joint within an ARTUS product may be commanded with a target angular position, angular velocity, and force.

This is achieved by writing a nested dictionary and calling the `set_joint_angles()` method.

For example, to move the pinky of an ARTUS Lite into its closed state, this may look like:

```python
from artusapi import ArtusAPI

lite = ArtusAPI(...)

pinky_dict = {"pinky_d2": {"index": 15, "target_angle": 90}}

lite.set_joint_angles(pinky_dict)
```

As seen in the example above, every joint is keyed by its **name**, with sub-keys for the **joint index** and the desired **angular position**, **angular velocity**, and **force output**.

This structure makes it possible to set joints directly via JSON files, as shown in the [excerpt from `/data/hand_posess/grasp_example.json`](/data/hand_poses/grasp_example.json) below.

```json
{
  "thumb_spread":
  {
  "index": 0,
    "target_angle": -25,
    "target_velocity": 50,
    "target_force": 40,
  },
  "thumb_flex":
  {
    "index": 1,
    "target_angle": 40,
    "target_velocity": 50,
    "target_force": 40,
  },
  "thumb_d2":
  {
    "index": 2,
    "target_angle": 40,
    "target_velocity": 40,
    "target_force": 40,
  },
  "thumb_d1":
  {
    "index": 3,
    "target_angle": 40,
    "target_velocity": 40,
    "target_force": 40,
  },
  ...
}
```

In the JSON snippet above, `target_velocity` and `target_force` parameters are also specified.
These fields are optional: when left empty, **the joint prioritizes the most recently commanded `target_velocity` and `target_force`** parameters.
Otherwise, on boot, all ARTUS products will fallback to their default velocity/force values, which can be found in their software-level definition in the [`/robot` directory](/artusapi/robot/).

Joint indices and key names depend on the relevant ARTUS product model.
Please refer to the product-specific documentation located in the [top-level README](/README.md) to locate your required joint map.

| Parameter         | Description                                                                                                                                                                                                                                                                                                                 |       Units        |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------: |
| `index`           | The joint's index within the joint map corresponding to the `robot_type` of the **ArtusAPI** object.                                                                                                                                                                                                                        |         -          |
| `target_angle`    | An integer value representing the desired angular position setpoint. **A more positive value corresponds to a more closed, while a more negative value represents a more open position**                                                                                                                                    |      Degrees       |
| `target_velocity` | An integer value representing the desired angular velocity setpoint. When in **position control mode**, the velocity setpoint is treated as an **absolute value**. When in **velocity control mode**, a positive value corresponds to a **closing motion**, while a negative value represents an **opening motion**         | Degrees per second |
| `target_force`    | A float value representing the desired force setpoint from the joint. When in **position OR velocity control mode**, the force setpoint is treated as an **absolute value**. When in **torque control mode**, a positive value corresponds to a **closing motion**, while a negative value represents an **opening motion** |      Newtons       |

## Next steps: Retrieving Feedback

[The following document describes the next steps to retrieve feedback from an ARTUS product.](/docs/software/usage/feedback.md)
