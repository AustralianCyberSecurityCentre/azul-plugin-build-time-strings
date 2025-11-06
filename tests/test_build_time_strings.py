from azul_runner import FV, Event, Filepath, JobResult, State, Uri, test_template

from azul_plugin_build_time_strings.main import AzulPluginBuildTimeStrings


class TestBuildTimeStrings(test_template.TestPlugin):
    PLUGIN_TO_TEST = AzulPluginBuildTimeStrings

    def test_sample_1(self):
        """
        Run the plugin on a real sample and ensure we get the expected results.
        """
        # Unwrap some test data and run our plugin on it.
        sample_data = self.load_test_file_bytes(
            "bbc057651ad416e59c1f036c031654db76be009128eedf3f4e3917f3ff8df5f7", "Reverse shell windows 32 DLL."
        )
        result = self.do_execution(data_in=[("content", sample_data)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="bbc057651ad416e59c1f036c031654db76be009128eedf3f4e3917f3ff8df5f7",
                        features={
                            "build_time_string": [
                                FV("rev_shell_2020021303282669_amd64", label="UTC -8.0", offset=99329, size=32),
                                FV("rev_shell_2020021303282669_amd64.dll", label="UTC -8.0", offset=99362, size=36),
                            ]
                        },
                    )
                ],
            ),
        )

    def test_sample_2(self):
        """
        Run the plugin on a real sample and ensure we get the expected results.
        """
        # Unwrap some test data and run our plugin on it.
        sample_data = self.load_test_file_bytes(
            "d1a9d80646a7f939bd03b11e13854dcbd52ab7326d6a445eed49dd6aa7f4898d", "Reverse shell windows 32 DLL."
        )
        result = self.do_execution(data_in=[("content", sample_data)])
        self.assertJobResult(
            result,
            JobResult(
                state=State(State.Label.COMPLETED),
                events=[
                    Event(
                        entity_type="binary",
                        entity_id="d1a9d80646a7f939bd03b11e13854dcbd52ab7326d6a445eed49dd6aa7f4898d",
                        features={
                            "build_time_string": [
                                FV("alfa_2020040402433338_x86", label="UTC -7.0", offset=86849, size=25),
                                FV("alfa_2020040402433338_x86.dll", label="UTC -7.0", offset=86875, size=29),
                            ]
                        },
                    )
                ],
            ),
        )
