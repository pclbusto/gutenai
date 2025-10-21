#!/usr/bin/env python3
"""
EpubCheck Wrapper y Parser
Módulo para ejecutar epubcheck y parsear sus resultados en GutenAI
"""

import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum


class MessageLevel(Enum):
    """Niveles de severidad de los mensajes de epubcheck"""
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    USAGE = "USAGE"
    INFO = "INFO"


class ValidationProfile(Enum):
    """Perfiles de validación disponibles en epubcheck"""
    DEFAULT = "default"
    DICT = "dict"
    EDUPUB = "edupub"
    IDX = "idx"
    PREVIEW = "preview"


@dataclass
class EpubLocation:
    """Representa una ubicación específica de un error/advertencia"""
    path: str
    line: Optional[int] = None
    column: Optional[int] = None
    context: Optional[str] = None


@dataclass
class EpubMessage:
    """Representa un mensaje de validación de epubcheck"""
    id: str
    severity: MessageLevel
    message: str
    locations: List[EpubLocation] = field(default_factory=list)
    additional_locations: int = 0
    suggestion: Optional[str] = None


@dataclass
class EpubItem:
    """Representa un item del EPUB según epubcheck"""
    id: str
    fileName: str
    media_type: Optional[str]
    compressedSize: int
    uncompressedSize: int
    compressionMethod: str
    checkSum: str
    isSpineItem: bool
    spineIndex: Optional[int]
    isLinear: bool
    referencedItems: List[str] = field(default_factory=list)


@dataclass
class EpubPublication:
    """Información de la publicación EPUB"""
    title: Optional[str] = None
    creator: List[str] = field(default_factory=list)
    publisher: Optional[str] = None
    date: Optional[str] = None
    subject: List[str] = field(default_factory=list)
    description: Optional[str] = None
    rights: Optional[str] = None
    identifier: Optional[str] = None
    language: Optional[str] = None
    nSpines: int = 0
    ePubVersion: Optional[str] = None
    isScripted: bool = False
    hasFixedFormat: bool = False
    hasAudio: bool = False
    hasVideo: bool = False
    charsCount: int = 0
    embeddedFonts: List[str] = field(default_factory=list)
    refFonts: List[str] = field(default_factory=list)
    hasEncryption: bool = False
    hasSignatures: bool = False
    contributors: List[str] = field(default_factory=list)


@dataclass
class EpubChecker:
    """Información del checker de epubcheck"""
    path: str
    filename: str
    checkerVersion: str
    checkDate: str
    elapsedTime: int
    nFatal: int = 0
    nError: int = 0
    nWarning: int = 0
    nUsage: int = 0


@dataclass
class EpubCheckResult:
    """Resultado completo de la validación epubcheck"""
    checker: EpubChecker
    publication: EpubPublication
    messages: List[EpubMessage] = field(default_factory=list)
    items: List[EpubItem] = field(default_factory=list)
    customMessageFileName: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Retorna True si el EPUB no tiene errores fatales o errores"""
        return self.checker.nFatal == 0 and self.checker.nError == 0

    @property
    def has_warnings(self) -> bool:
        """Retorna True si el EPUB tiene advertencias"""
        return self.checker.nWarning > 0

    @property
    def total_issues(self) -> int:
        """Total de problemas encontrados"""
        return self.checker.nFatal + self.checker.nError + self.checker.nWarning


class EpubCheckWrapper:
    """Wrapper para ejecutar epubcheck y parsear resultados"""

    def __init__(self, epubcheck_command: str = "epubcheck"):
        """
        Inicializa el wrapper

        Args:
            epubcheck_command: Comando para ejecutar epubcheck (por defecto "epubcheck")
        """
        self.epubcheck_command = epubcheck_command
        self.logger = logging.getLogger(__name__)

    def check_installation(self) -> Tuple[bool, str]:
        """
        Verifica si epubcheck está instalado y disponible

        Returns:
            Tuple[bool, str]: (está_instalado, versión_o_error)
        """
        try:
            result = subprocess.run(
                [self.epubcheck_command, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
            else:
                return False, f"Error al ejecutar epubcheck: {result.stderr}"
        except FileNotFoundError:
            return False, "epubcheck no encontrado. Asegúrate de que esté instalado y en el PATH."
        except subprocess.TimeoutExpired:
            return False, "Timeout al ejecutar epubcheck"
        except Exception as e:
            return False, f"Error inesperado: {str(e)}"

    def validate_epub(
        self,
        epub_path: Union[str, Path],
        profile: ValidationProfile = ValidationProfile.DEFAULT,
        include_usage: bool = False,
        fail_on_warnings: bool = False,
        message_filter: Optional[str] = None
    ) -> EpubCheckResult:
        """
        Valida un archivo EPUB usando epubcheck

        Args:
            epub_path: Ruta al archivo EPUB
            profile: Perfil de validación a usar
            include_usage: Incluir información de uso
            fail_on_warnings: Fallar también en advertencias
            message_filter: Filtro de mensajes (fatal, error, warn)

        Returns:
            EpubCheckResult: Resultado de la validación

        Raises:
            FileNotFoundError: Si el archivo EPUB no existe
            subprocess.CalledProcessError: Si epubcheck falla
            json.JSONDecodeError: Si la salida JSON es inválida
        """
        epub_path = Path(epub_path)
        if not epub_path.exists():
            raise FileNotFoundError(f"Archivo EPUB no encontrado: {epub_path}")

        # Construir comando
        cmd = [
            self.epubcheck_command,
            str(epub_path),
            "--json", "-"  # Salida JSON a stdout
        ]

        # Agregar opciones
        if profile != ValidationProfile.DEFAULT:
            cmd.extend(["--profile", profile.value])

        if include_usage:
            cmd.append("--usage")

        if fail_on_warnings:
            cmd.append("--failonwarnings")

        if message_filter:
            cmd.extend([f"--{message_filter}"])

        self.logger.info(f"Ejecutando: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # Timeout de 60 segundos
            )

            # epubcheck puede retornar código != 0 incluso con salida válida
            if result.stdout:
                return self._parse_json_result(result.stdout)
            else:
                error_msg = result.stderr or "No se recibió salida de epubcheck"
                raise subprocess.CalledProcessError(result.returncode, cmd, stderr=error_msg)

        except subprocess.TimeoutExpired:
            raise subprocess.CalledProcessError(-1, cmd, stderr="Timeout al ejecutar epubcheck")
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al parsear JSON: {e}")
            self.logger.error(f"Salida recibida: {result.stdout}")
            raise

    def _parse_json_result(self, json_output: str) -> EpubCheckResult:
        """
        Parsea la salida JSON de epubcheck

        Args:
            json_output: Salida JSON de epubcheck

        Returns:
            EpubCheckResult: Resultado parseado
        """
        data = json.loads(json_output)

        # Parsear checker info
        checker_data = data.get("checker", {})
        checker = EpubChecker(
            path=checker_data.get("path", ""),
            filename=checker_data.get("filename", ""),
            checkerVersion=checker_data.get("checkerVersion", ""),
            checkDate=checker_data.get("checkDate", ""),
            elapsedTime=checker_data.get("elapsedTime", 0),
            nFatal=checker_data.get("nFatal", 0),
            nError=checker_data.get("nError", 0),
            nWarning=checker_data.get("nWarning", 0),
            nUsage=checker_data.get("nUsage", 0)
        )

        # Parsear publication info
        pub_data = data.get("publication", {})
        publication = EpubPublication(
            title=pub_data.get("title"),
            creator=pub_data.get("creator", []),
            publisher=pub_data.get("publisher"),
            date=pub_data.get("date"),
            subject=pub_data.get("subject", []),
            description=pub_data.get("description"),
            rights=pub_data.get("rights"),
            identifier=pub_data.get("identifier"),
            language=pub_data.get("language"),
            nSpines=pub_data.get("nSpines", 0),
            ePubVersion=pub_data.get("ePubVersion"),
            isScripted=pub_data.get("isScripted", False),
            hasFixedFormat=pub_data.get("hasFixedFormat", False),
            hasAudio=pub_data.get("hasAudio", False),
            hasVideo=pub_data.get("hasVideo", False),
            charsCount=pub_data.get("charsCount", 0),
            embeddedFonts=pub_data.get("embeddedFonts", []),
            refFonts=pub_data.get("refFonts", []),
            hasEncryption=pub_data.get("hasEncryption", False),
            hasSignatures=pub_data.get("hasSignatures", False),
            contributors=pub_data.get("contributors", [])
        )

        # Parsear mensajes
        messages = []
        for msg_data in data.get("messages", []):
            try:
                level = MessageLevel(msg_data.get("severity", "INFO"))
            except ValueError:
                level = MessageLevel.INFO

            # Parsear ubicaciones
            locations = []
            for loc_data in msg_data.get("locations", []):
                location = EpubLocation(
                    path=loc_data.get("path", ""),
                    line=loc_data.get("line"),
                    column=loc_data.get("column"),
                    context=loc_data.get("context")
                )
                locations.append(location)

            message = EpubMessage(
                id=msg_data.get("ID", ""),
                severity=level,
                message=msg_data.get("message", ""),
                locations=locations,
                additional_locations=msg_data.get("additionalLocations", 0),
                suggestion=msg_data.get("suggestion")
            )
            messages.append(message)

        # Parsear items
        items = []
        for item_data in data.get("items", []):
            item = EpubItem(
                id=item_data.get("id", ""),
                fileName=item_data.get("fileName", ""),
                media_type=item_data.get("media_type"),
                compressedSize=item_data.get("compressedSize", 0),
                uncompressedSize=item_data.get("uncompressedSize", 0),
                compressionMethod=item_data.get("compressionMethod", ""),
                checkSum=item_data.get("checkSum", ""),
                isSpineItem=item_data.get("isSpineItem", False),
                spineIndex=item_data.get("spineIndex"),
                isLinear=item_data.get("isLinear", False),
                referencedItems=item_data.get("referencedItems", [])
            )
            items.append(item)

        return EpubCheckResult(
            checker=checker,
            publication=publication,
            messages=messages,
            items=items,
            customMessageFileName=data.get("customMessageFileName")
        )

    def validate_epub_simple(self, epub_path: Union[str, Path]) -> Tuple[bool, List[str]]:
        """
        Validación simple que retorna solo si es válido y lista de errores

        Args:
            epub_path: Ruta al archivo EPUB

        Returns:
            Tuple[bool, List[str]]: (es_válido, lista_de_errores)
        """
        try:
            result = self.validate_epub(epub_path)
            errors = []

            for message in result.messages:
                if message.severity in [MessageLevel.FATAL, MessageLevel.ERROR]:
                    errors.append(f"{message.severity.value}: {message.message}")

            return result.is_valid, errors

        except Exception as e:
            return False, [f"Error al ejecutar epubcheck: {str(e)}"]


# Funciones de conveniencia
def quick_validate(epub_path: Union[str, Path]) -> Tuple[bool, List[str]]:
    """
    Función de conveniencia para validación rápida

    Args:
        epub_path: Ruta al archivo EPUB

    Returns:
        Tuple[bool, List[str]]: (es_válido, lista_de_errores)
    """
    wrapper = EpubCheckWrapper()
    return wrapper.validate_epub_simple(epub_path)


def get_epub_info(epub_path: Union[str, Path]) -> Optional[EpubPublication]:
    """
    Función de conveniencia para obtener información del EPUB

    Args:
        epub_path: Ruta al archivo EPUB

    Returns:
        EpubPublication: Información del EPUB o None si hay error
    """
    try:
        wrapper = EpubCheckWrapper()
        result = wrapper.validate_epub(epub_path)
        return result.publication
    except Exception:
        return None


if __name__ == "__main__":
    # Test básico
    import sys

    if len(sys.argv) < 2:
        print("Uso: python epubcheck_wrapper.py <archivo.epub>")
        sys.exit(1)

    epub_file = sys.argv[1]

    wrapper = EpubCheckWrapper()

    # Verificar instalación
    installed, version = wrapper.check_installation()
    if not installed:
        print(f"Error: {version}")
        sys.exit(1)

    print(f"Usando {version}")

    try:
        result = wrapper.validate_epub(epub_file)

        print(f"\n=== Validación de {result.checker.filename} ===")
        print(f"Versión EPUB: {result.publication.ePubVersion}")
        print(f"Título: {result.publication.title}")
        print(f"Autor(es): {', '.join(result.publication.creator)}")
        print(f"Idioma: {result.publication.language}")
        print(f"Caracteres: {result.publication.charsCount:,}")
        print(f"Elementos en spine: {result.publication.nSpines}")

        print(f"\n=== Resultados ===")
        print(f"Errores fatales: {result.checker.nFatal}")
        print(f"Errores: {result.checker.nError}")
        print(f"Advertencias: {result.checker.nWarning}")
        print(f"Tiempo: {result.checker.elapsedTime}ms")

        if result.messages:
            print(f"\n=== Mensajes ===")
            for msg in result.messages:
                print(f"[{msg.severity.value}] {msg.message}")

        print(f"\n=== Estado ===")
        if result.is_valid:
            print("✓ EPUB VÁLIDO")
        else:
            print("✗ EPUB INVÁLIDO")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)