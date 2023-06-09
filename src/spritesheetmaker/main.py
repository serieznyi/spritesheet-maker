import argparse
from datetime import datetime
import logging
import math
import os
import importlib.metadata

from typing import Any
from pathlib import Path
from PIL import Image

PACKAGE_NAME = "spritesheet-maker"
DEFAULT_COLUMNS_COUNT = 5

# Logging
FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('main')
logger.setLevel(logging.DEBUG)

def chunks(values, chunk_size) -> list[list[Any]]:
    """Yield successive n-sized chunks from lst."""

    chunks = []
    for i in range(0, len(values), chunk_size):
        chunks.append(values[i:i + chunk_size])

    return chunks

def read_images(source_dir: Path, chunk_size: int | None) -> list[list[Path]]:
    files = sorted(source_dir.glob('*.*'))
    images = []

    for current_file in files:
        logger.debug("Read file: %s" % current_file)
        try:
            with Image.open(current_file) as im:
                images.append(im.getdata())
        except Exception as e:
            raise RuntimeError("'%s' is not a valid image" % current_file, e)

    images_count = len(images)
    chunk_size = images_count if not chunk_size else chunk_size

    if images_count > 0:
        logger.info("Source images count: %s" % images_count)

    return chunks(images, chunk_size)

def generate_sprite_sheet_from_images_chunk(
        images: list[Path],
        output_dir: Path,
        chunk_number: int,
        rows: int | None,
        columns: int | None,
        spritesheet_name = str | None
) -> None:
    max_columns = columns if columns else DEFAULT_COLUMNS_COUNT
    max_rows = rows if rows else math.ceil(len(images) / DEFAULT_COLUMNS_COUNT)

    logger.info("Grid size: columns = %s, rows = %s" % (max_columns, max_rows))

    tile_width = images[0].size[0]
    tile_height = images[0].size[1]

    sprite_sheet_width = int(tile_width * max_columns)
    sprite_sheet_height = tile_height * max_rows

    sprite_sheet = Image.new("RGBA", (sprite_sheet_width, sprite_sheet_height))

    for frame in images:
        cropped_frame = frame.crop((0, 0, tile_width, tile_height))
        frame_index = images.index(frame)

        if frame_index > max_rows * max_columns:
            print("Break. Images more than need for grid")
            break

        # (x1,y1)------------|
        #    |               |
        #    |               |
        #    |------------(x2,y2)
        x1 = tile_height * (frame_index % max_columns)
        y1 = tile_width * math.floor(frame_index / max_columns)

        x2 = x1 + tile_width
        y2 = y1 + tile_height

        box = (x1, y1, x2, y2)

        sprite_sheet.paste(cropped_frame, box)

    if spritesheet_name:
        sprite_sheet_file_name = "%s-%02d.png" % (spritesheet_name, chunk_number)
    else:
        sprite_sheet_file_name = "spritesheet_" + datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f") + ".png"

    output_file = Path(output_dir, sprite_sheet_file_name)
    sprite_sheet.save(output_file, "PNG")

    logger.info("generated sprite path: %s" % output_file)

def generate_sprite_sheets(
        source_dir: Path,
        output_dir: Path,
        rows: int | None,
        columns: int | None,
        chunk_size = int | None,
        spritesheet_name = str | None
) -> None:
    logger.info("Source dir: %s" % source_dir)
    logger.info("Output dir: %s" % output_dir)

    images_chunks = read_images(source_dir, chunk_size)

    if len(images_chunks) == 0:
        logger.warning("Source dir is empty")
        return

    for i, chunk in enumerate(images_chunks):
        chunk_number=i+1
        logger.info("Generate chunk %s" % chunk_number)
        generate_sprite_sheet_from_images_chunk(chunk, output_dir, chunk_number, rows, columns, spritesheet_name)

def main():
    options = parse_args()

    logger.setLevel(eval('logging.' + options.logLevel.upper()))

    generate_sprite_sheets(
        source_dir=options.sourceDir,
        output_dir=options.outputDir,
        chunk_size=options.chunkSize,
        rows=options.rows,
        columns=options.columns,
        spritesheet_name=options.spritesheetName,
    )

def get_program_version() -> str:
    return importlib.metadata.version(PACKAGE_NAME)

def argparse_validation_dir_path(mode: int):
    """
    :type mode: os.R_OK or os.W_OK
    """

    def validator(value):
        directory = Path(value)

        if not directory.is_dir():
            raise argparse.ArgumentTypeError("Not a directory: %s" % value)

        if mode == os.R_OK and not os.access(directory, os.R_OK):
            raise argparse.ArgumentTypeError("File %s not readable" % value)
        elif mode == os.W_OK and not os.access(directory, os.W_OK):
            raise argparse.ArgumentTypeError("File %s not writable" % value)

        return directory.resolve()

    return validator


def argparse_validation_spritesheet_name(value):
    try:
        value = str(value)
        print(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Must be a string")
    if not len(value):
        raise argparse.ArgumentTypeError("Argument must be at least 1 character")
    return value


def argparse_validation_int(minimal_value: int = 1):
    def validation(value):
        try:
            value = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError("Must be a integer number")
        if value < minimal_value:
            raise argparse.ArgumentTypeError("Argument must be > " + str(minimal_value))
        return value

    return validation


def parse_args():
    parser = argparse.ArgumentParser(
        description='''
                Generate spritesheet image
            ''',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'sourceDir',
        type=argparse_validation_dir_path(os.R_OK),
        help="Directory with source images for spritesheet generating"
    )

    parser.add_argument(
        'outputDir',
        type=argparse_validation_dir_path(os.W_OK),
        help="Directory for result"
    )

    parser.add_argument(
        '--rows',
        type=argparse_validation_int(1),
        help="Columns count"
    )

    parser.add_argument(
        '--columns',
        type=argparse_validation_int(1),
        help="Rows count"
    )

    parser.add_argument(
        '--chunkSize',
        type=argparse_validation_int(1),
        help="Split images from source dir on chunks"
    )

    parser.add_argument(
        '--spritesheetName',
        type=argparse_validation_spritesheet_name,
        help="Prefix name for created spritesheet without extension. Chunk number will be added as postfix."
    )

    parser.add_argument(
        '--logLevel',
        default='info',
        help="Logging level. Default: info",
        choices=['info', 'debug', 'warn']
    )

    parser.add_argument(
        '--version',
        help="Show version of program",
        action="version",
        version=get_program_version()
    )

    return parser.parse_args()

if __name__ == '__main__':
    main()
