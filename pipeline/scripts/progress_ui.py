"""Fenêtre minimale de suivi des tests et reconstructions du workspace."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
TEST_PLANNER = SCRIPT_DIR / "test_changed.py"
WORKSPACE_PLANNER = SCRIPT_DIR / "workspace.py"
TEST_LABELS = {"Aucun": "none", "Ciblés": "targeted", "Complets": "full"}
RECONSTRUCTION_LABELS = {"Aucune": "none", "Ciblées": "targeted", "Toutes": "all"}


@dataclass(frozen=True)
class PlanningRequest:
    source: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionStep:
    source: str
    scope: str
    label: str
    argv: tuple[str, ...]


def planning_requests(
    test_mode: str,
    reconstruction_mode: str,
    *,
    verify_determinism: bool = False,
    python: str = sys.executable,
) -> tuple[PlanningRequest, ...]:
    if test_mode not in TEST_LABELS.values():
        raise ValueError(f"unsupported test mode: {test_mode}")
    if reconstruction_mode not in RECONSTRUCTION_LABELS.values():
        raise ValueError(f"unsupported reconstruction mode: {reconstruction_mode}")
    requests: list[PlanningRequest] = []
    if test_mode != "none":
        flag = "--targeted" if test_mode == "targeted" else "--full"
        requests.append(
            PlanningRequest("tests", (python, str(TEST_PLANNER), flag, "--json"))
        )
    if reconstruction_mode != "none":
        selection = (
            ("--changed",)
            if reconstruction_mode == "targeted"
            else ("--scope", "all")
        )
        argv = [python, str(WORKSPACE_PLANNER), "refresh", *selection]
        if verify_determinism:
            argv.append("--verify-determinism")
        requests.append(PlanningRequest("reconstructions", (*argv, "--json")))
    return tuple(requests)


def steps_from_payload(
    payload: Mapping[str, object], source: str
) -> tuple[ExecutionStep, ...]:
    commands = payload.get("commands")
    if not isinstance(commands, list):
        raise ValueError(f"plan {source}: champ commands absent ou invalide")
    steps: list[ExecutionStep] = []
    for index, command in enumerate(commands, 1):
        if not isinstance(command, dict):
            raise ValueError(f"plan {source}: commande {index} invalide")
        label = command.get("label")
        scope = command.get("scope")
        argv = command.get("argv")
        valid = (
            isinstance(label, str)
            and bool(label)
            and isinstance(scope, str)
            and bool(scope)
            and isinstance(argv, list)
            and bool(argv)
            and all(isinstance(value, str) and value for value in argv)
        )
        if not valid:
            raise ValueError(f"plan {source}: commande {index} incomplète")
        steps.append(ExecutionStep(source, scope, label, tuple(argv)))
    return tuple(steps)


def summarize_payload(payload: Mapping[str, object], source: str) -> str:
    if source == "tests":
        commands = payload.get("commands")
        count = len(commands) if isinstance(commands, list) else 0
        if payload.get("mode") == "targeted":
            modules = payload.get("python_modules")
            module_count = len(modules) if isinstance(modules, list) else 0
            return f"Tests ciblés : {module_count} module(s), {count} étape(s)"
        return f"Tests complets : {count} étape(s)"
    scopes = payload.get("scopes")
    names = ", ".join(map(str, scopes)) if isinstance(scopes, list) else "aucune"
    suffix = " ; déterminisme ×2" if payload.get("verify_determinism") is True else ""
    return f"Reconstructions : {names or 'aucune'}{suffix}"


def process_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(PYTHONUTF8="1", PYTHONUNBUFFERED="1")
    return environment


def load_plan(
    requests: Iterable[PlanningRequest],
) -> tuple[tuple[ExecutionStep, ...], tuple[str, ...]]:
    steps: list[ExecutionStep] = []
    summaries: list[str] = []
    for request in requests:
        completed = subprocess.run(
            request.argv,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=process_environment(),
            check=False,
        )
        if completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Planification {request.source} impossible : {detail}")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Plan JSON {request.source} invalide : {error}") from error
        if not isinstance(payload, dict):
            raise RuntimeError(f"Plan JSON {request.source} invalide")
        steps.extend(steps_from_payload(payload, request.source))
        summaries.append(summarize_payload(payload, request.source))
    return tuple(steps), tuple(summaries)


def run_execution_steps(
    steps: Iterable[ExecutionStep],
    events: queue.Queue[tuple[object, ...]],
    *,
    keep_going: bool = False,
    popen_factory: object = subprocess.Popen,
) -> None:
    """Run a fixed plan and optionally aggregate failures across its steps."""

    failures: list[tuple[int, str, str]] = []
    for index, step in enumerate(steps):
        events.put(("started", index, step.label))
        try:
            process = popen_factory(  # type: ignore[operator]
                step.argv,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=process_environment(),
            )
            if process.stdout:
                for line in process.stdout:
                    events.put(("log", line))
            code = process.wait()
            detail = f"code de sortie {code}" if code else ""
        except Exception as error:
            detail = str(error) or type(error).__name__
        if detail:
            failures.append((index, step.label, detail))
            events.put(("failed", index, detail, keep_going))
            if not keep_going:
                return
        else:
            events.put(("done", index))
    if failures:
        events.put(("finished-with-failures", tuple(failures)))
    else:
        events.put(("finished",))


class ProgressApplication:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue[tuple[object, ...]] = queue.Queue()
        self.steps: tuple[ExecutionStep, ...] = ()
        self.signature: tuple[str, str, bool] | None = None
        self.running = False
        self.started_at: float | None = None
        self.step_started_at: float | None = None
        self.active_label = ""
        self.test_choice = tk.StringVar(value="Ciblés")
        self.reconstruction_choice = tk.StringVar(value="Aucune")
        self.determinism = tk.BooleanVar(value=False)
        self.keep_going = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Choisissez un plan, puis cliquez sur Planifier.")
        self.elapsed = tk.StringVar(value="Temps : 00:00")
        self.current = tk.StringVar(value="Aucune étape active")
        self._build()
        for variable in (
            self.test_choice,
            self.reconstruction_choice,
            self.determinism,
        ):
            variable.trace_add("write", self._invalidate)
        self._invalidate()
        self.status.set("Choisissez un plan, puis cliquez sur Planifier.")
        root.protocol("WM_DELETE_WINDOW", self._close)
        root.after(100, self._poll)
        root.after(500, self._tick)

    def _build(self) -> None:
        self.root.title("Validation BG2 Upscale")
        self.root.geometry("760x600")
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(9, weight=1)
        ttk.Label(main, text="Tests").grid(row=0, column=0, sticky="w", pady=3)
        self.test_box = ttk.Combobox(
            main, textvariable=self.test_choice, values=tuple(TEST_LABELS), state="readonly"
        )
        self.test_box.grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(main, text="Reconstructions").grid(row=1, column=0, sticky="w", pady=3)
        self.reconstruction_box = ttk.Combobox(
            main,
            textvariable=self.reconstruction_choice,
            values=tuple(RECONSTRUCTION_LABELS),
            state="readonly",
        )
        self.reconstruction_box.grid(row=1, column=1, sticky="w", pady=3)
        self.determinism_box = ttk.Checkbutton(
            main, text="Déterminisme (double les reconstructions)", variable=self.determinism
        )
        self.determinism_box.grid(row=2, column=1, sticky="w")
        self.keep_going_box = ttk.Checkbutton(
            main,
            text="Continuer après erreur (récapitulatif final)",
            variable=self.keep_going,
        )
        self.keep_going_box.grid(row=3, column=1, sticky="w")
        buttons = ttk.Frame(main)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)
        self.plan_button = ttk.Button(buttons, text="Planifier", command=self._plan)
        self.plan_button.pack(side="left")
        self.start_button = ttk.Button(buttons, text="Démarrer", command=self._start)
        self.start_button.pack(side="left", padx=8)
        ttk.Label(buttons, textvariable=self.elapsed).pack(side="right")
        ttk.Label(main, textvariable=self.status, wraplength=720).grid(
            row=5, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(main, text="Ensemble").grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.overall = ttk.Progressbar(main, mode="determinate", maximum=1)
        self.overall.grid(row=6, column=1, sticky="ew", pady=(8, 0))
        ttk.Label(main, text="Étape active").grid(row=7, column=0, sticky="w", pady=(6, 0))
        self.active = ttk.Progressbar(main, mode="indeterminate")
        self.active.grid(row=7, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(main, textvariable=self.current).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=4
        )
        self.listbox = tk.Listbox(main, height=8)
        self.listbox.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(4, 8))
        self.log = scrolledtext.ScrolledText(
            main, height=9, state="disabled", font=("Consolas", 9)
        )
        self.log.grid(row=10, column=0, columnspan=2, sticky="nsew")
        self.start_button.configure(state="disabled")

    def _selection(self) -> tuple[str, str, bool]:
        return (
            TEST_LABELS[self.test_choice.get()],
            RECONSTRUCTION_LABELS[self.reconstruction_choice.get()],
            self.determinism.get(),
        )

    def _invalidate(self, *_args: object) -> None:
        if self.running:
            return
        if RECONSTRUCTION_LABELS[self.reconstruction_choice.get()] == "none":
            if self.determinism.get():
                self.determinism.set(False)
            self.determinism_box.configure(state="disabled")
        else:
            self.determinism_box.configure(state="normal")
        if self.signature != self._selection():
            self.steps = ()
            self.start_button.configure(state="disabled")
            self.status.set("Sélection modifiée : planification requise.")

    def _controls(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.plan_button.configure(state=state)
        self.test_box.configure(state="readonly" if enabled else "disabled")
        self.reconstruction_box.configure(state="readonly" if enabled else "disabled")
        self.start_button.configure(state=state if enabled and self.steps else "disabled")
        reconstruction = RECONSTRUCTION_LABELS[self.reconstruction_choice.get()]
        self.determinism_box.configure(
            state=state if enabled and reconstruction != "none" else "disabled"
        )
        self.keep_going_box.configure(state=state)

    def _plan(self) -> None:
        selection = self._selection()
        if selection[:2] == ("none", "none"):
            messagebox.showinfo("Plan vide", "Sélectionnez des tests ou des reconstructions.")
            return
        self.running = True
        self.steps = ()
        self.signature = None
        self.started_at = None
        self.elapsed.set("Temps : 00:00")
        self._reset_view()
        self._controls(False)
        self.status.set("Planification en cours…")
        threading.Thread(target=self._plan_worker, args=(selection,), daemon=True).start()

    def _plan_worker(self, selection: tuple[str, str, bool]) -> None:
        try:
            result = load_plan(
                planning_requests(*selection[:2], verify_determinism=selection[2])
            )
            self.events.put(("planned", selection, *result))
        except Exception as error:
            self.events.put(("error", "Planification impossible", str(error)))

    def _start(self) -> None:
        if not self.steps or self.signature != self._selection():
            messagebox.showwarning("Plan requis", "Planifiez la sélection courante.")
            return
        writes = any(step.source == "reconstructions" for step in self.steps)
        message = f"Exécuter les {len(self.steps)} étape(s) affichées ?"
        if writes:
            message += "\n\nLes projections générées seront mises à jour."
        if self.keep_going.get():
            message += "\n\nLes étapes suivantes continueront après un échec."
        if not messagebox.askyesno("Confirmer l’exécution", message):
            return
        self.running = True
        self.started_at = time.monotonic()
        self._reset_view()
        self._controls(False)
        threading.Thread(
            target=self._run_worker,
            args=(self.keep_going.get(),),
            daemon=True,
        ).start()

    def _run_worker(self, keep_going: bool) -> None:
        run_execution_steps(self.steps, self.events, keep_going=keep_going)

    def _poll(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "planned":
                    self.running = False
                    self.signature, self.steps, summaries = event[1], event[2], event[3]
                    self._reset_view()
                    self.status.set(" | ".join(summaries))
                    self._controls(True)
                elif kind == "started":
                    index, label = int(event[1]), str(event[2])
                    self.step_started_at = time.monotonic()
                    self.active_label = f"{index + 1}/{len(self.steps)} — {label}"
                    self._set_line(index, "▶")
                    self.active.start(12)
                    self._append(f"\n== {label} ==\n")
                elif kind == "log":
                    self._append(str(event[1]))
                elif kind == "done":
                    index = int(event[1])
                    self._set_line(index, "✓", self._step_time())
                    self.overall.configure(value=index + 1)
                    self.active.stop()
                elif kind == "failed":
                    index, detail, continuing = int(event[1]), str(event[2]), bool(event[3])
                    self._set_line(index, "✗", self._step_time())
                    self.overall.configure(value=index + 1)
                    self.active.stop()
                    if not continuing:
                        self._finish(f"Échec à l’étape {index + 1} : {detail}")
                        messagebox.showerror("Exécution interrompue", self.status.get())
                elif kind == "finished":
                    self._finish("Plan terminé avec succès.")
                    self.current.set("Toutes les étapes sont terminées")
                elif kind == "finished-with-failures":
                    failures = event[1]
                    count = len(failures) if isinstance(failures, tuple) else 0
                    detail = "\n".join(
                        f"Étape {int(item[0]) + 1} — {item[1]} : {item[2]}"
                        for item in failures
                    )
                    self._finish(f"Plan terminé avec {count} échec(s).")
                    self.current.set("Toutes les étapes ont été tentées")
                    messagebox.showerror("Exécution terminée avec erreurs", detail)
                elif kind == "error":
                    self._finish(str(event[2]))
                    messagebox.showerror(str(event[1]), str(event[2]))
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _reset_view(self) -> None:
        self.listbox.delete(0, "end")
        for step in self.steps:
            self.listbox.insert("end", f"· [{step.source}/{step.scope}] {step.label}")
        self.overall.configure(maximum=max(1, len(self.steps)), value=0)
        self.current.set("Aucune étape active")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _set_line(self, index: int, marker: str, duration: str = "") -> None:
        step = self.steps[index]
        suffix = f" ({duration})" if duration else ""
        self.listbox.delete(index)
        self.listbox.insert(index, f"{marker} [{step.source}/{step.scope}] {step.label}{suffix}")
        self.listbox.see(index)

    def _append(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _finish(self, status: str) -> None:
        self.active.stop()
        self.active_label = ""
        self.step_started_at = None
        self.running = False
        self.status.set(status)
        self._controls(True)

    def _tick(self) -> None:
        if self.running and self.started_at is not None:
            duration = self._format_duration(time.monotonic() - self.started_at)
            self.elapsed.set(f"Temps : {duration}")
        if self.active_label and self.step_started_at is not None:
            duration = self._format_duration(time.monotonic() - self.step_started_at)
            self.current.set(f"{self.active_label} — {duration}")
        self.root.after(500, self._tick)

    def _step_time(self) -> str:
        started = self.step_started_at or time.monotonic()
        return self._format_duration(time.monotonic() - started)

    @staticmethod
    def _format_duration(value: float) -> str:
        elapsed = max(0, int(value))
        minutes, seconds = divmod(elapsed, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def _close(self) -> None:
        if self.running:
            messagebox.showwarning("Exécution active", "Attendez la fin avant de fermer.")
        else:
            self.root.destroy()


def main() -> int:
    root = tk.Tk()
    ProgressApplication(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
