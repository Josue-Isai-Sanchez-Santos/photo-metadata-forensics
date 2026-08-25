from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


DEFAULT_HASH_ALGORITHM = "sha256"

SUPPORTED_HASH_ALGORITHMS = (
    "sha256",
    "sha1",
    "md5",
)


class HashingError(Exception):
    """Base exception for hashing errors."""


def normalize_hash_algorithm(
    algorithm: str,
) -> str:
    """
    Normaliza nombres habituales:

        SHA-256 -> sha256
        SHA256  -> sha256
        SHA-1   -> sha1
        MD5     -> md5
    """

    normalized = (
        algorithm
        .strip()
        .lower()
        .replace("-", "")
    )

    if (
        normalized
        not in SUPPORTED_HASH_ALGORITHMS
    ):
        raise HashingError(
            "Algoritmo hash no soportado: "
            f"{algorithm!r}"
        )

    return normalized


def calculate_hash(
    path: str | Path,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = 1024 * 1024,
) -> str:
    """
    Calcula un hash del contenido completo
    de un archivo.

    SHA-256 es el algoritmo predeterminado.
    """

    hashes = calculate_hashes(
        path,
        algorithms=(algorithm,),
        chunk_size=chunk_size,
    )

    normalized = normalize_hash_algorithm(
        algorithm
    )

    return hashes[normalized]


def calculate_hashes(
    path: str | Path,
    algorithms: Iterable[str] = (
        DEFAULT_HASH_ALGORITHM,
    ),
    chunk_size: int = 1024 * 1024,
) -> dict[str, str]:
    """
    Calcula uno o varios hashes leyendo
    el archivo una sola vez.
    """

    file_path = Path(path)

    if not file_path.exists():
        raise HashingError(
            f"El archivo no existe: {file_path}"
        )

    if not file_path.is_file():
        raise HashingError(
            f"La ruta no es un archivo: "
            f"{file_path}"
        )

    if chunk_size <= 0:
        raise HashingError(
            "chunk_size debe ser mayor que cero."
        )

    normalized_algorithms: list[str] = []

    for algorithm in algorithms:

        normalized = normalize_hash_algorithm(
            algorithm
        )

        if (
            normalized
            not in normalized_algorithms
        ):
            normalized_algorithms.append(
                normalized
            )

    if not normalized_algorithms:
        raise HashingError(
            "Debe especificarse al menos "
            "un algoritmo hash."
        )

    hashers = {
        algorithm: _create_hasher(
            algorithm
        )
        for algorithm
        in normalized_algorithms
    }

    with file_path.open("rb") as file:

        while True:

            chunk = file.read(
                chunk_size
            )

            if not chunk:
                break

            for hasher in hashers.values():
                hasher.update(
                    chunk
                )

    return {
        algorithm: hasher.hexdigest()
        for algorithm, hasher
        in hashers.items()
    }


def calculate_sha256(
    path: str | Path,
) -> str:

    return calculate_hash(
        path,
        "sha256",
    )


def calculate_sha1(
    path: str | Path,
) -> str:

    return calculate_hash(
        path,
        "sha1",
    )


def calculate_md5(
    path: str | Path,
) -> str:

    return calculate_hash(
        path,
        "md5",
    )


def compare_files_by_hash(
    first: str | Path,
    second: str | Path,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
) -> bool:
    """
    Compara dos archivos por digest.

    Por defecto utiliza SHA-256.
    """

    first_digest = calculate_hash(
        first,
        algorithm,
    )

    second_digest = calculate_hash(
        second,
        algorithm,
    )

    return (
        first_digest
        == second_digest
    )


def _create_hasher(
    algorithm: str,
):
    """
    Crea el objeto hashlib apropiado.

    MD5 y SHA-1 se permiten exclusivamente
    para identificación/compatibilidad,
    no como recomendación criptográfica.
    """

    if algorithm == "sha256":
        return hashlib.sha256()

    if algorithm == "sha1":
        return hashlib.sha1(
            usedforsecurity=False
        )

    if algorithm == "md5":
        return hashlib.md5(
            usedforsecurity=False
        )

    raise HashingError(
        "Algoritmo hash interno "
        f"no soportado: {algorithm}"
    )
