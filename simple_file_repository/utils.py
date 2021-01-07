import magic


def guess_mime_type(content: bytes) -> str:
    """Return a mime type for given content.

    :param content: beginning of the file.
    :return: a string with mime type (`application/octet-stream` in worst case)
    """

    with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
        mime_type = m.id_buffer(content)
        # returns application/octet-stream in worst case
        return mime_type
