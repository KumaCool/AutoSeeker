import contextlib
import importlib
import io
import os
import sys


@contextlib.contextmanager
def silent_import():
    sys.stdout.flush()
    sys.stderr.flush()
    stdout = sys.__stdout__ or sys.stdout
    stderr = sys.__stderr__ or sys.stderr
    saved_stdout = os.dup(stdout.fileno())
    saved_stderr = os.dup(stderr.fileno())
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, stdout.fileno())
        os.dup2(devnull, stderr.fileno())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yield
    finally:
        os.dup2(saved_stdout, stdout.fileno())
        os.dup2(saved_stderr, stderr.fileno())
        os.close(saved_stdout)
        os.close(saved_stderr)
        os.close(devnull)


def import_iv8_silent():
    try:
        with silent_import():
            return importlib.import_module("iv8")
    except ImportError as exc:
        raise RuntimeError(
            "API 返回 code=37，但当前环境未安装经确认来源的 iv8。"
            "请按项目提供方说明安装正确的 iv8 wheel，不要直接安装不明同名包。"
        ) from exc
