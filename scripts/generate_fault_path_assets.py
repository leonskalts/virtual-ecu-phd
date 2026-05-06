#!/usr/bin/env python3
"""Generate lightweight PNG assets for the GUI fault-path tab."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = PROJECT_ROOT / "assets" / "fault_path"

LINE = "#476072"
ACCENT = "#4E84C4"
WARM = "#D46E52"
COOL = "#5F8F88"
MUTED = "#A7B6C2"


def setup_figure() -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(1.8, 1.15), dpi=120)
    fig.patch.set_alpha(0)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 84)
    ax.axis("off")
    return fig, ax


def save_icon(name: str, draw_fn) -> None:
    fig, ax = setup_figure()
    draw_fn(ax)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSET_DIR / f"{name}.png", dpi=120, transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def rounded_box(ax: plt.Axes, xy: tuple[float, float], width: float, height: float, edge: str, face: str = "white") -> None:
    ax.add_patch(
        FancyBboxPatch(
            xy,
            width,
            height,
            boxstyle="round,pad=0.02,rounding_size=5",
            linewidth=2,
            edgecolor=edge,
            facecolor=face,
        )
    )


def draw_sensor(ax: plt.Axes) -> None:
    ax.plot([14, 96], [18, 18], color=LINE, linewidth=3)
    ax.add_patch(Arc((24, 18), 18, 18, theta1=0, theta2=180, linewidth=3, color=LINE))
    ax.plot([62, 62], [28, 64], color=ACCENT, linewidth=3)
    ax.add_patch(Circle((62, 47), 10, fill=False, linewidth=2.5, edgecolor=ACCENT))
    ax.add_patch(Circle((62, 43), 4, color=WARM))
    ax.plot([48, 56], [64, 64], color=COOL, linewidth=2)
    ax.plot([56, 64], [64, 64], color=COOL, linewidth=2)
    ax.plot([64, 72], [64, 64], color=COOL, linewidth=2)
    ax.plot([52, 52], [60, 68], color=COOL, linewidth=2)


def draw_timing_link(ax: plt.Axes) -> None:
    rounded_box(ax, (10, 26), 22, 22, LINE)
    rounded_box(ax, (88, 26), 22, 22, LINE)
    for x in (40, 52, 64):
        ax.add_patch(Rectangle((x, 34), 6, 6, linewidth=0, facecolor=ACCENT))
    ax.add_patch(
        FancyArrowPatch((30, 37), (86, 37), arrowstyle="-|>", mutation_scale=12, linewidth=2.5, linestyle="--", color=LINE)
    )
    ax.plot([28, 94], [58, 58], color=MUTED, linewidth=2)
    ax.plot([82, 90], [54, 58], color=MUTED, linewidth=2)
    ax.plot([82, 90], [62, 58], color=MUTED, linewidth=2)
    ax.text(61, 48, "...", ha="center", va="center", color="#7C8D99", fontsize=10, fontweight="bold")


def draw_ecu(ax: plt.Axes) -> None:
    rounded_box(ax, (10, 18), 46, 48, ACCENT, face="#F6FAFE")
    rounded_box(ax, (70, 24), 34, 36, LINE)
    ax.add_patch(Rectangle((22, 30), 22, 22, linewidth=2, edgecolor=ACCENT, facecolor="white"))
    for y in (26, 34, 42, 50, 58):
        ax.plot([10, 6], [y, y], color=ACCENT, linewidth=2)
        ax.plot([56, 60], [y, y], color=ACCENT, linewidth=2)
    for y in (34, 42, 50):
        ax.plot([76, 96], [y, y], color=LINE, linewidth=2)
    ax.plot([56, 70], [42, 42], color=MUTED, linewidth=2.5)


def draw_actuator(ax: plt.Axes) -> None:
    rounded_box(ax, (10, 22), 24, 34, LINE)
    ax.plot([34, 68], [39, 39], color=LINE, linewidth=2.5)
    fan_center = (88, 39)
    ax.add_patch(Circle(fan_center, 15, fill=False, linewidth=2.5, edgecolor=ACCENT))
    ax.add_patch(Polygon([(88, 39), (99, 34), (92, 44)], closed=True, fill=False, edgecolor=ACCENT, linewidth=2))
    ax.add_patch(Polygon([(88, 39), (82, 50), (93, 45)], closed=True, fill=False, edgecolor=ACCENT, linewidth=2))
    ax.add_patch(Polygon([(88, 39), (77, 34), (84, 28)], closed=True, fill=False, edgecolor=ACCENT, linewidth=2))
    ax.add_patch(Circle(fan_center, 3, color=ACCENT))
    ax.plot([16, 28], [50, 50], color=WARM, linewidth=2)
    ax.plot([16, 28], [44, 44], color=WARM, linewidth=2)
    ax.plot([16, 28], [38, 38], color=WARM, linewidth=2)


def draw_plant(ax: plt.Axes) -> None:
    rounded_box(ax, (18, 20), 58, 40, COOL, face="#F4FBFA")
    for y in (28, 36, 44, 52):
        ax.plot([28, 66], [y, y], color=COOL, linewidth=2)
    ax.plot([76, 92], [30, 30], color=WARM, linewidth=3)
    ax.plot([76, 92], [48, 48], color=WARM, linewidth=3)
    ax.add_patch(Circle((98, 39), 10, fill=False, linewidth=2.5, edgecolor=WARM))
    ax.add_patch(Circle((98, 35), 4, color=WARM))
    ax.plot([98, 98], [35, 45], color=WARM, linewidth=2.5)


def main() -> None:
    save_icon("sensor_adc", draw_sensor)
    save_icon("timing_link", draw_timing_link)
    save_icon("ecu_control_memory", draw_ecu)
    save_icon("actuator_power", draw_actuator)
    save_icon("thermal_plant", draw_plant)


if __name__ == "__main__":
    main()
