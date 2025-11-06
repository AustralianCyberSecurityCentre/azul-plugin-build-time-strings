"""Find timestamp strings in Windows executables near their PE compile time.

This can help infer timezone of build chain or other interesting features.
"""

from azul_runner import FV, BinaryPlugin, Feature, Job, add_settings, cmdline_run

from .library import extract_features


class AzulPluginBuildTimeStrings(BinaryPlugin):
    """Find timestamp strings in Windows executables near their PE compile time."""

    CONTACT = "ASD's ACSC"
    VERSION = "2025.02.07"

    FEATURES = [Feature("build_time_string", "String containing a time close to the compile time.")]

    SETTINGS = add_settings(
        filter_max_content_size=(int, 10 * 1024 * 1024),
        filter_data_types={
            "content": [
                "executable/windows/dll32",
                "executable/windows/dll64",
                "executable/windows/pe",
                "executable/windows/pe32",
                "executable/windows/pe64",
                "executable/dll32",
                "executable/pe32",
            ]
        },
    )

    def execute(self, job: Job):
        """Run across any windows executable with content."""
        build_time_features = []

        # We'll receive a list of tuples. These will contain a string which
        # contains a date/time close the compilation time of the file, and
        # another string which represents a possible timezone, based on a
        # comparison between the date and the compile time.
        features = extract_features(job.get_data().read())
        for context, timezone, offset in features:
            # The main value will be the string featuring the datetime, but
            # we'll use the timezone string as a label, rather than its own
            # feature.
            feature_value = FV(context, label=timezone, offset=offset, size=len(context))
            build_time_features.append(feature_value)

        self.add_feature_values("build_time_string", build_time_features)


def main():
    """Run plugin via command-line."""
    cmdline_run(plugin=AzulPluginBuildTimeStrings)


if __name__ == "__main__":
    main()
