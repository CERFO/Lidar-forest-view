import logging
import os
import re
import sys
import threading
import warnings
import zipfile
from datetime import date


def _archive_log_to_zip(log_path, archive_dir):
    """Compresse le fichier .log en .zip dans archive_dir et supprime le .log. Ne fait rien en cas d'erreur."""
    if not log_path or not os.path.isfile(log_path):
        return
    base_name = os.path.basename(log_path)
    if not base_name.endswith(".log"):
        return
    os.makedirs(archive_dir, exist_ok=True)
    zip_path = os.path.join(archive_dir, base_name + ".zip")
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(log_path, arcname=base_name)
        os.remove(log_path)
    except OSError:
        pass


class DailyRotatingFileHandler(logging.Handler):
    """
    Écrit dans log/YYYY-MM-DD.log. Au premier écrit d'un nouveau jour,
    ferme le fichier précédent, l'archive en .zip dans log/archive/, archive aussi tout .log restant, puis ouvre le fichier du jour.
    """

    _log_filename_re = re.compile(r"^(\d{4}-\d{2}-\d{2})\.log$")

    def __init__(self, log_dir, archive_subdir="archive"):
        super().__init__()
        self._log_dir = os.path.abspath(log_dir)
        self._archive_subdir = archive_subdir
        self._current_date = None
        self._current_file_path = None
        self._stream = None
        self._lock = threading.RLock()

    def _archive_dir(self):
        return os.path.join(self._log_dir, self._archive_subdir)

    def _open_for_date(self, d):
        """Ouvre le fichier de log pour la date d (objet date)."""
        name = d.isoformat() + ".log"
        path = os.path.join(self._log_dir, name)
        self._current_file_path = path
        self._current_date = d
        self._stream = open(path, "a", encoding="utf-8")

    def _archive_dangling_logs(self, today):
        """Archive tous les fichiers .log dans log_dir qui ne sont pas la date du jour (fichiers « en attente »)."""
        today_name = today.isoformat() + ".log"
        archive_dir = self._archive_dir()
        try:
            for name in os.listdir(self._log_dir):
                if name == today_name:
                    continue
                m = self._log_filename_re.match(name)
                if not m:
                    continue
                path = os.path.join(self._log_dir, name)
                if os.path.isfile(path):
                    _archive_log_to_zip(path, archive_dir)
        except OSError:
            pass

    def _rollover(self, today):
        """Ferme le fichier courant, l'archive en .zip dans archive/, archive les autres .log en attente, puis ouvre le fichier du jour."""
        if self._stream is not None:
            path = self._current_file_path
            self._stream.flush()
            self._stream.close()
            self._stream = None
            self._current_file_path = None
            self._current_date = None
            if path:
                _archive_log_to_zip(path, self._archive_dir())
        self._archive_dangling_logs(today)
        self._open_for_date(today)

    def emit(self, record):
        try:
            with self._lock:
                today = date.today()
                if self._stream is None:
                    os.makedirs(self._log_dir, exist_ok=True)
                    self._archive_dangling_logs(today)
                    self._open_for_date(today)
                elif today != self._current_date:
                    self._rollover(today)
                msg = self.format(record)
                if self._stream:
                    self._stream.write(msg + "\n")
                    self._stream.flush()
        except Exception:
            self.handleError(record)

    def close(self):
        with self._lock:
            if self._stream:
                try:
                    self._stream.close()
                except OSError:
                    pass
                self._stream = None
            self._current_file_path = None
            self._current_date = None
        super().close()


class _LoggerWriter:
    """Redirects writes to a logger at the given level, buffering by line."""

    def __init__(self, logger, level):
        self._logger = logger
        self._level = level
        self._buf = ""

    def write(self, msg):
        self._buf += msg
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._logger.log(self._level, line)

    def flush(self):
        if self._buf.strip():
            self._logger.log(self._level, self._buf)
            self._buf = ""

    def fileno(self):
        # Some libraries (e.g. VTK) call fileno(); return the real stderr fd
        return 2


_initialized = False


def setup_logging(log_dir=None):
    """Configure le logger racine avec un gestionnaire de fichier à bascule quotidienne."""
    global _initialized
    if _initialized:
        return
    _initialized = True
    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), "log")
    os.makedirs(log_dir, exist_ok=True)
    handler = DailyRotatingFileHandler(log_dir)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)

    # Route Python warnings (e.g. numpy RuntimeWarning) through logging
    logging.captureWarnings(True)

    # Route stderr (e.g. VTK errors) to the log file
    stderr_logger = logging.getLogger("stderr")
    sys.stderr = _LoggerWriter(stderr_logger, logging.ERROR)


def get_logger(name, log_dir=None):
    """Retourne un logger pour le nom donné. S'assure que setup_logging() a été appelé (avec log_dir par défaut si besoin)."""
    setup_logging(log_dir)
    return logging.getLogger(name)
