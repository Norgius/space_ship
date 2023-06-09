import os
import time
import curses
import argparse
import asyncio
from itertools import cycle
from random import randint, choice
from functools import partial

from environs import Env

from explosion import explode
from physics import update_speed
from game_scenario import PHRASES, get_garbage_delay_tics
from obstacles import Obstacle, show_obstacles
from curses_tools import draw_frame, read_controls, get_frame_size

TIC_TIMEOUT = 0.1
year = 1957


async def animate_spaceship(canvas, row, column, rocket_frames,
                            year_adding_weapons):
    row_speed, column_speed = 0, 0
    for rocket_frame in cycle(rocket_frames):
        for _ in range(2):
            draw_frame(canvas, row, column, rocket_frame)
            await sleep()

            draw_frame(canvas, row, column, rocket_frame, negative=True)
            rows_direction, columns_direction,\
                space_pressed = read_controls(canvas)
            row_speed, column_speed = update_speed(
                row_speed, column_speed, rows_direction, columns_direction
            )
            row += row_speed
            column += column_speed

            if year >= year_adding_weapons and space_pressed:
                coroutines.append(fire(canvas, row, column + 2))

            row = min(max(row_borders), max(min(row_borders), row))
            column = min(
                    max(column_borders),
                    max(min(column_borders), column)
                )

            for obstacle in obstacles:
                if obstacle.has_collision(
                        row, column, ship_width, ship_height):
                    coroutines.append(
                        explode(canvas, row + ship_width / 2,
                                column + ship_height / 2)
                    )
                    coroutines.append(
                        show_gameover(canvas, row_borders[1] / 2,
                                      column_borders[1] / 3)
                    )
                    return


async def blink(canvas, row, column, symbol, offset_tics):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(offset_tics)

        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


async def fire(canvas, start_row, start_column,
               rows_speed=-2.5, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await sleep()

    canvas.addstr(round(row), round(column), 'O')
    await sleep()

    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await sleep()
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed
        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                obstacles_in_last_collisions.append(obstacle)
                return


async def fly_garbage(canvas, column, garbage_frame, speed=0.2):
    """
    Animate garbage, flying from top to bottom.
    Сolumn position will stay same, as specified on start.
    """
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0
    rows_size, columns_size = get_frame_size(garbage_frame)

    obstacle = Obstacle(row, column, rows_size, columns_size)
    obstacles.append(obstacle)

    try:
        while row < rows_number:
            draw_frame(canvas, row, column, garbage_frame)
            obstacle.row = row
            await sleep()
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
            if obstacle in obstacles_in_last_collisions:
                explosion_row = obstacle.row + obstacle.rows_size / 2
                explosion_column = obstacle.column + obstacle.columns_size / 2
                coroutines.append(
                    explode(canvas, explosion_row, explosion_column)
                )
                break
    finally:
        obstacles.remove(obstacle)


async def fill_orbit_with_garbage(canvas, display_height):
    garbage = os.listdir('garbage')
    while True:
        delay_tics = get_garbage_delay_tics(year)
        if not delay_tics:
            await sleep(15)
            continue

        path_to_garbage_frames = os.path.join('garbage', choice(garbage))
        with open(path_to_garbage_frames, 'r') as garbage_file:
            frame = garbage_file.read()
        garbage_coord = randint(0, display_height)
        coroutines.append(
            fly_garbage(canvas, column=garbage_coord, garbage_frame=frame)
        )
        await sleep(delay_tics)


async def show_year(window_for_show_year):
    while True:
        year_information = f'{year} year\n{PHRASES.get(year, "")}'
        draw_frame(window_for_show_year, 0, 0, year_information)
        await sleep()
        draw_frame(window_for_show_year, 0, 0, year_information, negative=True)


async def spend_time():
    global year
    while True:
        await sleep(15)
        year += 1


async def show_gameover(canvas, row, column):
    with open('game_over_lettering.txt', 'r') as file:
        lettering = file.read()
    while True:
        draw_frame(canvas, row, column, lettering)
        await sleep()
        draw_frame(canvas, row, column, lettering, negative=True)


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


def draw(canvas, path_to_frames_dir, stars_number, year_adding_weapons):
    curses.curs_set(False)
    canvas.nodelay(True)
    rocket_frames = []
    for rocket_frame in os.listdir(path_to_frames_dir):
        with open(os.path.join(path_to_frames_dir, rocket_frame), 'r') as file:
            rocket_frames.append(file.read())
    display_width, display_height = canvas.getmaxyx()

    global ship_width
    global ship_height
    ship_width, ship_height = get_frame_size(rocket_frames[0])

    step_from_edge = 1
    max_offset_tics = 15

    global row_borders
    global column_borders
    row_borders = (step_from_edge, display_width - ship_width - step_from_edge)
    column_borders = (step_from_edge,
                      display_height - ship_height - step_from_edge)

    global coroutines
    global obstacles
    global obstacles_in_last_collisions
    obstacles, obstacles_in_last_collisions = [], []

    coroutines = [
        blink(
            canvas=canvas,
            row=randint(step_from_edge * 2,
                        display_width - step_from_edge * 2),
            column=randint(step_from_edge * 2,
                           display_height - step_from_edge * 2),
            symbol=choice('+*.:'),
            offset_tics=randint(0, max_offset_tics),
              ) for _ in range(stars_number)
    ]
    coroutines.append(
        animate_spaceship(
            canvas=canvas,
            row=row_borders[1] / 2,
            column=column_borders[1] / 3,
            rocket_frames=rocket_frames,
            year_adding_weapons=year_adding_weapons,
                          )
    )
    coroutines.append(fill_orbit_with_garbage(canvas, display_height))
    coroutines.append(show_obstacles(canvas, obstacles))

    window_for_show_year = canvas.derwin(0, 0)
    coroutines.append(spend_time())
    coroutines.append(show_year(window_for_show_year))
    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
                continue
        window_for_show_year.refresh()
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


def main():
    env = Env()
    env.read_env()
    stars_number = env.int('STARS_NUMBER', 200)
    year_adding_weapons = env.int(
        'YEAR_ADDING_WEAPONS_FOR_SPACESHIP', 2020
    )
    parser = argparse.ArgumentParser(
        description='Укажите путь к директории с макетами ракеты'
    )
    parser.add_argument('-path', default='rocket_frames',
                        help='Путь до директории')
    args = parser.parse_args()
    curses.update_lines_cols()
    curses.wrapper(
        partial(
            draw,
            path_to_frames_dir=args.path,
            stars_number=stars_number,
            year_adding_weapons=year_adding_weapons
                )
    )


if __name__ == '__main__':
    main()
