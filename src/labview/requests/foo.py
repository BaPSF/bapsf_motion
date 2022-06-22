def foo(request):
    """Dummy function for testing with `test_daq_caller.vi`"""

    if "spam" not in globals():
        globals()["spam"] = 1
    else:
        globals()["spam"] += 1

    return (
        f"Response: foo() received your request '{request}'.  The 'spam' global "
        f"variable is now {globals()['spam']}."
    )
