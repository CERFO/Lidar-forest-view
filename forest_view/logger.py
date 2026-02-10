import gzip
import logging
import os
import shutil
import threading
from datetime import date


class DailyRotatingFileHandler(logging.Handler):
    """
    Écrit dans log/YYYY-MM-DD.log. Au premier écrit d'un nouveau jour,
    ferme le fichier précédent, le compresse en YYYY-MM-DD.log.gz, puis ouvre le fichier du jour.
    """

    def __init__(self, log_dir, archive_subdir=None):
        super().__init__()
        self._log_dir = os.path.abspath(log_dir)
        self._archive_subdir = archive_subdir  # inutilisé pour l'instant ; on garde dans le même dossier
        self._current_date = None
        self._current_file_path = None
        self._stream = None
        self._lock = threading.RLock()

    def _open_for_date(self, d):
        """Ouvre le fichier de log pour la date d (objet date)."""
        name = d.isoformat() + ".log"
        path = os.path.join(self._log_dir, name)
        self._current_file_path = path
        self._current_date = d
        self._stream = open(path, "a", encoding="utf-8")

    def _rollover(self, today):
        """Ferme le fichier courant, le compresse en gzip, puis ouvre le fichier du jour."""
        if self._stream is None:
            return
        path = self._current_file_path
        self._stream.flush()
        self._stream.close()
        self._stream = None
        self._current_file_path = None
        self._current_date = None
        if path and os.path.isfile(path):
            gz_path = path + ".gz"
            try:
                with open(path, "rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(path)
            except OSError:
                pass  # laisser le .log en place si la compression ou la suppression échoue
        self._open_for_date(today)

    def emit(self, record):
        try:
            with self._lock:
                today = date.today()
                if self._stream is None:
                    os.makedirs(self._log_dir, exist_ok=True)
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
    # Le format de date par défaut du Formatter inclut date, heure et millisecondes (ex. 2025-02-09 10:30:00,123)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)


def get_logger(name, log_dir=None):
    """Retourne un logger pour le nom donné. S'assure que setup_logging() a été appelé (avec log_dir par défaut si besoin)."""
    setup_logging(log_dir)
    return logging.getLogger(name)
