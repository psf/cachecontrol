from mock import patch

from cachecontrol.patch_requests import (make_responses_pickleable,
                                         models)

class TestPatchingPickledResponses(object):

    @patch('requests.__version__', '1.0')
    def test_patch(self):
        make_responses_pickleable()

        assert models.Response.__getstate__
        assert models.Response.__setstate__

    @patch('requests.__version__', '2.0')
    def test_patch_on_two_point_0(self):
        make_responses_pickleable()

        assert models.Response.__getstate__
        assert models.Response.__setstate__

    @patch('requests.__version__', '2.2')
    def test_no_patch(self):
        make_responses_pickleable()

        assert models.Response.__getstate__
        assert models.Response.__setstate__

    @patch('requests.__version__', '3.0')
    def test_no_patch_anymore(self):
        make_responses_pickleable()

        assert models.Response.__getstate__
        assert models.Response.__setstate__
