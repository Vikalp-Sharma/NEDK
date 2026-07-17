<div align="center">

```
███╗   ██╗███████╗ ██████╗ ███╗   ██╗
████╗  ██║██╔════╝██╔═══██╗████╗  ██║
██╔██╗ ██║█████╗  ██║   ██║██╔██╗ ██║
██║╚██╗██║██╔══╝  ██║   ██║██║╚██╗██║
██║ ╚████║███████╗╚██████╔╝██║ ╚████║
╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝
██████╗ ██╗   ██╗███╗   ██╗███╗   ██╗███████╗██████╗
██╔══██╗██║   ██║████╗  ██║████╗  ██║██╔════╝██╔══██╗
██████╔╝██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝
██╔══██╗██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗
██║  ██║╚██████╔╝██║ ╚████║██║ ╚████║███████╗██║  ██║
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
```

### an endless runner for a 3.2" Raspberry Pi touchscreen

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.x-05EAD1?style=flat-square&logo=pygame)](https://www.pygame.org/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Touchscreen-C51A4A?style=flat-square&logo=raspberrypi)](https://www.raspberrypi.com/)
[![Display](https://img.shields.io/badge/320×180-Resolution-8A2BE2?style=flat-square)](#)
[![60 FPS](https://img.shields.io/badge/60-FPS-00E676?style=flat-square)](#)
[![License](https://img.shields.io/badge/License-No--Copy-B900F8?style=flat-square)](./LICENSE)

</div>

<br>

## Overview

**Neon Runner** is a self-contained, single-file endless runner built
for a 3.2" resistive/capacitive touchscreen bolted to a Raspberry Pi.
No mouse, no keyboard required — just two thumbs and three lanes
standing between you and a very high score.

Dodge spike walls, ceiling spikes, laser gates, gap pillars, and
homing missiles while a procedurally generated neon city scrolls by
under a pulsing purple moon. Every runner has a fully hand-drawn
idle/run/death animation — no sprite sheets, no external assets,
everything is vector-drawn at runtime.

## Features

- **4 playable characters** — Duck, Frog, Robot, Cat
- **5 obstacle types** — ground spikes, ceiling spikes, gap pillars, pulsing laser gates, homing missiles
- **3-lane vertical movement** with squash/stretch jump physics
- **Fully procedural** parallax city skyline, starfield, and grid floor
- **Particle system** — trails, sparks, death bursts, score popups
- **Touch gestures** — tap or swipe, upper/lower half split
- **Zero external assets** — every pixel is drawn in code
- **Auto-fullscreen** on boot when no `DISPLAY` is detected (Pi-ready)

## Controls

| Input | Zone | Action |
|---|---|---|
| Tap / swipe up | Upper half of screen | **Jump** (move up a lane) |
| Tap / swipe down | Lower half of screen | **Duck** (move down a lane) |
| `↑` Arrow key | Keyboard (dev only) | Jump |
| `↓` Arrow key | Keyboard (dev only) | Duck |
| `Esc` | Keyboard (dev only) | Back to menu |

Character select is a single tap — pick a runner and you're dropped
straight back to the main menu. No confirm screen, no back button.

## Getting started

```bash
pip install pygame
python3 neon_runner.py
```

On a Raspberry Pi with no `DISPLAY` set, it launches fullscreen and
borderless automatically — plug in the touchscreen and go.

## Tech notes

| | |
|---|---|
| **Engine** | pygame, software surfaces, additive-blend glow effects |
| **Resolution** | 320 × 180 @ 60 FPS |
| **Rendering** | per-frame vector draw, no sprite sheets |
| **Lanes** | 3 fixed Y-positions, spring-interpolated transitions |
| **Input** | `FINGERDOWN` / `FINGERUP` events, mouse fallback for dev |
| **Structure** | single file, state machine (`MENU` / `CHAR` / `PLAYING` / `GAMEOVER`) |

## License

This project is released under a **No-Copy License** — see [`LICENSE`](./LICENSE).

You may view and run this code. You may **not** copy, redistribute,
rehost, rebrand, resell, or repackage this project or any substantial
part of it without explicit written permission from the author.

<div align="center">
<sub>built by <b>max_cyan</b></sub>
</div>
