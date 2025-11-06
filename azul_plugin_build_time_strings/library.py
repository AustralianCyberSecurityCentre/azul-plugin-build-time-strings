"""Command-line tool and lib for finding interesting build strings."""

import argparse
import re
import string
import sys
from datetime import datetime, timedelta, timezone

import pefile

# The furthest apart the compile time / found string can be for us to consider
# it related to the build process.
MAX_SECONDS_DIFF = 60


def get_compile_time(file_data):
    """Extract compile time from a PE file and return as a datetime."""
    try:
        pe = pefile.PE(data=file_data, fast_load=False)

    except pefile.PEFormatError:
        return None

    compile_timestamp = pe.FILE_HEADER.TimeDateStamp
    compiled = datetime.fromtimestamp(compile_timestamp, timezone.utc)

    return compiled


def build_search_patterns(target):
    """Generate regex patterns to find build timestamp strings.

    Patterns to match within +- 12 hours of the target datetime are generated.
    """
    # Timezones could shift it +- 12 hours. Some delay in the build time itself
    # could potentially tip us forwards across a day/month/year boundary, so
    # we'll widen the range by a minute just to be safe.
    delta = timedelta(hours=12, minutes=1)
    earliest = target - delta
    latest = target + delta

    # We'll collect up to 32 printable characters which precede / follow the
    # date strings we're looking for, to provide context for our matches.
    # The core date portion will be in a group.
    printable = "[%s]{,32}" % "".join("\\x%02X" % ord(x) for x in string.printable)
    pattern_format = printable + "(%s)" + printable

    # The core of each pattern is a regex for a datetime string with format
    # like: YYYYMMDDHHMMSS. With our earliest/latest dates we can have fixed
    # data down to the day field (e.g 20200314) and we'll wildcard the rest.
    patterns = []
    for time in [earliest, target, latest]:
        pattern = pattern_format % time.strftime("%Y%m%d" + r"\d{6}")

        # We're searching binary data so our patterns must have type bytes.
        bpattern = bytes(pattern, encoding="utf-8")
        if bpattern not in patterns:
            patterns.append(bpattern)

    # Return a list of patterns, we only used a set so we'd produce unique
    # patterns.
    return patterns


def find_datetime_strings(file_data, target):
    """Find timestamp strings within +- 12 hour of the target datetime.

    Specifically, strings in the following format are searched:

        YYYYMMDDHHMMSS
    e.g.
        20200314235959
    """
    # Generate search patterns for the target datetime.
    patterns = build_search_patterns(target)

    # Search for instances of these patterns.
    for pattern in patterns:
        for match in re.finditer(pattern, file_data):
            # Yield the offset where it was located, and the datetime which it
            # represents.
            offset = match.start()
            context = match.group(0).decode("utf-8")
            date_string = match.group(1).decode("utf-8")
            candidate = datetime.strptime(date_string, "%Y%m%d%H%M%S")
            yield offset, candidate, context


def round_hours(hours):
    """Round some fraction of hours to the nearest hour or half hour.

    Return the rounded result, along with the remainder, so that we know
    how close it was.
    """
    # Round to the nearest hour / half-hour.
    rounded = round(hours * 2) / 2
    remainder = hours - rounded
    return rounded, remainder


def compare_times(target, candidate):
    """Compare the given candidate datetime against the target.

    Assume that the candidate datetime could be in any timezone, and check
    whether it is sufficiently close to the target time (which is in UTC).
    """
    # We'll need to pretend the candidate is in UTC so that we can compute
    # the difference between them.
    candidate = candidate.replace(tzinfo=timezone.utc)

    hours_diff = (candidate - target).total_seconds() / 3600

    # Round our difference to the nearest half hour, plus or minus some
    # remainder.
    rounded, remainder = round_hours(hours_diff)

    # Ensure it is in a range which could be caused by timezones.
    if abs(rounded) > 12:
        return None

    # Ensure it is sufficiently close to our target time.
    if abs(remainder * 60 * 60) > MAX_SECONDS_DIFF:
        return None

    return "UTC %+.1f" % rounded


def extract_features(file_data):
    """Search the given PE file for timestamp strings near the compile time."""
    # Get a datetime from the PE's compile timestamp.
    compiled = get_compile_time(file_data)
    if not compiled:
        return None

    features = []

    # Find datetime strings which could represent times very close to the
    # compile time.
    for offset, candidate, context in find_datetime_strings(file_data, compiled):
        # Check whether this candidate is close enough to the compile time, and
        # if it is, what timezone it appears to be under.
        possible_timezone = compare_times(compiled, candidate)
        if possible_timezone:
            # Add to our list of features.
            features.append((context, possible_timezone, offset))

    return features


def main():
    """Search the provided file for build time strings."""
    # Use argparse to provide a user interface and collect arguments.
    description = "Find strings representing times near the compile time."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("filepath", help="PE file to search for time strings.")
    args = parser.parse_args()

    # Load data from the given file.
    with open(args.filepath, "rb") as f:
        file_data = f.read()

    # We only want to run on PE files.
    if file_data[:2] != b"\x4d\x5a":
        sys.exit(0)

    # Extract and display features.
    features = extract_features(file_data)
    if features:
        # It's nice to display the compile timestamp for visual comparison with
        # the resulting features.
        compiled = get_compile_time(file_data)
        print("Compile Timestamp: %s" % compiled)
        print("Possible build time strings:")

    for context, tz, offset in features:
        print("\t0x%X: %s (%s)" % (offset, context, tz))


if __name__ == "__main__":
    main()
