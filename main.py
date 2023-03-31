import os
import time
import curses
import argparse
import asyncio
from itertools import cycle
from random import randint, choice
from functools import partial

from curses_tools import draw_frame, read_controls, get_frame_size

TIC_TIMEOUT = 0.1


async def animate_spaceship(canvas, row, column, rocket_frames):
    for rocket_frame in cycle(rocket_frames):
        draw_frame(canvas, row, column, rocket_frame)
        await asyncio.sleep(0)

        draw_frame(canvas, row, column, rocket_frame, negative=True)
        rows_direction, columns_direction,\
            space_pressed = read_controls(canvas)
        if rows_direction or columns_direction:
            row += rows_direction
            row = min(max(row_borders), max(min(row_borders), row))

            column += columns_direction
            column = min(max(column_borders), max(min(column_borders), column))


async def blink(canvas, row, column, symbol, offset_tics):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(offset_tics):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(20):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)


async def fire(canvas, start_row, start_column,
               rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


def draw(canvas, path_to_frames_dir):
    curses.curs_set(False)
    canvas.border()
    canvas.nodelay(True)
    rocket_frames = []
    for rocket_frame in os.listdir(path_to_frames_dir):
        with open(os.path.join(path_to_frames_dir, rocket_frame), 'r') as file:
            rocket_frames.append(file.read())
    display_width, display_height = canvas.getmaxyx()
    ship_width, ship_height = get_frame_size(rocket_frames[0])

    global row_borders
    global column_borders
    step_from_edge = 1
    row_borders = (step_from_edge, display_width - ship_width - step_from_edge)
    column_borders = (step_from_edge,
                      display_height - ship_height - step_from_edge)
    step_from_border = 2
    max_offset_tics = 15
    coroutines = [
        blink(
            canvas=canvas,
            row=randint(step_from_border, display_width - step_from_border),
            column=randint(step_from_border,
                           display_height - step_from_border),
            symbol=choice('+*.:'),
            offset_tics=randint(0, max_offset_tics),
              ) for _ in range(200)
    ]
    coroutines.append(
        animate_spaceship(
            canvas=canvas,
            row=row_borders[1] / 2,
            column=column_borders[1] / 3,
            rocket_frames=rocket_frames
                          )
    )
    coroutines.append(fire(canvas, display_width - 2, display_height / 2))
    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
                canvas.refresh()
            except StopIteration:
                coroutines.remove(coroutine)
                continue
        time.sleep(TIC_TIMEOUT)


def main():
    parser = argparse.ArgumentParser(
        description='Укажите путь к директории с макетами ракеты'
    )
    parser.add_argument('-path', default='rocket_frames',
                        help='Путь до директории')
    args = parser.parse_args()
    curses.update_lines_cols()
    curses.wrapper(partial(draw, path_to_frames_dir=args.path))


if __name__ == '__main__':
    main()
