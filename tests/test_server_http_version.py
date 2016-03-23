import requests


def test_http11(url):
    resp = requests.get(url)

    # Making sure our test server speaks HTTP/1.1
    assert resp.raw._fp.version == 11
