# enhanced_watcher.py - Detectar quién hace la segunda escritura

import os
import sys
import time
import psutil
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DetailedLogWrites(FileSystemEventHandler):
    def __init__(self, watch_file: Path):
        self.watch_file = watch_file.resolve()
        self.last_write_time = 0
        self.write_count = 0
        
    def on_modified(self, event):
        if Path(event.src_path).resolve() == self.watch_file:
            current_time = time.time()
            self.write_count += 1
            
            print(f"\n[WRITE #{self.write_count}] {self.watch_file}")
            print(f"  Time: {time.strftime('%H:%M:%S', time.localtime(current_time))}")
            print(f"  mtime: {os.path.getmtime(self.watch_file)}")
            
            if self.last_write_time > 0:
                delay = current_time - self.last_write_time
                print(f"  Delay from last write: {delay:.2f}s")
            
            # Detectar procesos que tienen el archivo abierto
            self.find_processes_using_file()
            
            # Usar lsof si está disponible (Linux/Mac)
            self.use_lsof()
            
            # Usar fuser si está disponible (Linux)
            self.use_fuser()
            
            self.last_write_time = current_time
    
    def find_processes_using_file(self):
        """Encuentra procesos que tienen el archivo abierto usando psutil"""
        print("  Processes with file open:")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Revisar archivos abiertos por el proceso
                    files = proc.open_files()
                    for file in files:
                        if Path(file.path).resolve() == self.watch_file:
                            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else 'N/A'
                            print(f"    PID {proc.info['pid']}: {proc.info['name']} - {cmdline}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"    Error with psutil: {e}")
    
    def use_lsof(self):
        """Usar lsof para detectar procesos (Linux/Mac)"""
        try:
            result = subprocess.run(
                ['lsof', str(self.watch_file)], 
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                print("  lsof output:")
                for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                    print(f"    {line}")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass  # lsof no disponible o error
    
    def use_fuser(self):
        """Usar fuser para detectar procesos (Linux)"""
        try:
            result = subprocess.run(
                ['fuser', '-v', str(self.watch_file)], 
                capture_output=True, text=True, timeout=2
            )
            if result.stderr.strip():  # fuser output va a stderr
                print("  fuser output:")
                for line in result.stderr.strip().split('\n'):
                    if not line.startswith('                     USER'):  # Skip header
                        print(f"    {line}")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass  # fuser no disponible


# MÉTODO 2: Monkey-patch dentro de tu aplicación
class ApplicationFileMonitor:
    """Monitorea desde dentro de la aplicación Python"""
    
    def __init__(self):
        self.original_open = None
        self.original_write = None
        self.monitored_files = set()
    
    def start_monitoring(self, files_to_monitor):
        """Intercepta operaciones de archivo desde Python"""
        import builtins
        
        self.monitored_files = {Path(f).resolve() for f in files_to_monitor}
        self.original_open = builtins.open
        
        def traced_open(file, mode='r', **kwargs):
            file_path = Path(file).resolve()
            
            if file_path in self.monitored_files and any(m in mode for m in ['w', 'a', '+']):
                import traceback
                print(f"\n[PYTHON WRITE] {file_path}")
                print(f"  Mode: {mode}")
                print("  Python Stack Trace:")
                for line in traceback.format_stack()[-5:-1]:  # Last 4 frames
                    print(f"    {line.strip()}")
            
            return self.original_open(file, mode, **kwargs)
        
        builtins.open = traced_open
    
    def stop_monitoring(self):
        """Restaura funciones originales"""
        if self.original_open:
            import builtins
            builtins.open = self.original_open


# MÉTODO 3: Usar strace para capturar system calls (Linux)
def trace_with_strace(pid, output_file):
    """Traza system calls del proceso especificado"""
    print(f"Iniciando strace en PID {pid}...")
    try:
        cmd = [
            'strace', 
            '-p', str(pid), 
            '-e', 'write,openat,close', 
            '-o', output_file,
            '-f'  # Follow forks
        ]
        
        process = subprocess.Popen(cmd)
        print(f"strace ejecutándose... Output en {output_file}")
        print("Presiona Ctrl+C para detener")
        
        try:
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            print(f"\nstrace detenido. Revisa {output_file} para detalles.")
    
    except FileNotFoundError:
        print("strace no está disponible en este sistema")


# MÉTODO 4: Detectar GtkSource auto-save en tu aplicación
def debug_gtksource_buffer(source_buffer):
    """Detecta si GtkSource está auto-guardando"""
    
    # Verificar propiedades del buffer
    for attr in dir(source_buffer):
        if 'save' in attr.lower() or 'auto' in attr.lower():
            try:
                value = getattr(source_buffer, attr)
                print(f"  {attr}: {value}")
            except:
                print(f"  {attr}: <method>")
    
    # Override del método de guardado si existe
    if hasattr(source_buffer, 'save_to_file'):
        original_save = source_buffer.save_to_file
        
        def traced_save(*args, **kwargs):
            import traceback
            print("\n[GTKSOURCE SAVE]")
            print("Stack trace:")
            traceback.print_stack()
            return original_save(*args, **kwargs)
        
        source_buffer.save_to_file = traced_save


# Función principal mejorada
def watch_file_detailed(path: str, enable_app_monitoring=False):
    """Watcher con múltiples métodos de detección"""
    
    p = Path(path).resolve()
    print(f"Watching: {p}")
    
    # Método 1: Watchdog
    handler = DetailedLogWrites(p)
    obs = Observer()
    obs.schedule(handler, p.parent.as_posix(), recursive=False)
    obs.start()
    
    # Método 2: Monitor desde Python (opcional)
    app_monitor = None
    if enable_app_monitoring:
        app_monitor = ApplicationFileMonitor()
        app_monitor.start_monitoring([path])
    
    try:
        print("Monitoring started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        obs.stop()
        obs.join()
        if app_monitor:
            app_monitor.stop_monitoring()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file_to_watch> [--trace-python] [--strace-pid PID]")
        print("  --trace-python: Also monitor Python file operations")
        print("  --strace-pid PID: Run strace on specific process ID")
        sys.exit(1)
    
    file_to_watch = sys.argv[1]
    enable_python_trace = '--trace-python' in sys.argv
    
    # Opción strace
    if '--strace-pid' in sys.argv:
        try:
            pid_idx = sys.argv.index('--strace-pid') + 1
            pid = int(sys.argv[pid_idx])
            strace_output = f"strace_{pid}.out"
            trace_with_strace(pid, strace_output)
        except (IndexError, ValueError):
            print("Error: --strace-pid requiere un PID válido")
            sys.exit(1)
    else:
        watch_file_detailed(file_to_watch, enable_python_trace)