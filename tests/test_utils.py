import magic

from simple_file_repository.utils import guess_mime_type


def test_libmagic_guess_image(sample_image):
    with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
        peek = sample_image[0:500]
        mime_type = m.id_buffer(peek)
        assert mime_type == "image/jpeg"


def test_guess_image(sample_image):
    buffer = sample_image[0:500]
    mime_type = guess_mime_type(buffer)
    assert mime_type == "image/jpeg"


def test_guess_unknown():
    buffer = b"just\x04bytes"
    mime_type = guess_mime_type(buffer)
    assert mime_type == "application/octet-stream"


def test_guess_text():
    buffer = b"just plain text"
    mime_type = guess_mime_type(buffer)
    assert mime_type == "text/plain"
