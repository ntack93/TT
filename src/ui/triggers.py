from typing import List, Dict, Any
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass

@dataclass
class Trigger:
    """Trigger configuration container."""
    pattern: str
    response: str
    enabled: bool = True

class TriggerManager:
    """Manages automated response triggers."""
    
    def __init__(self, master: tk.Tk, persistence: Any, telnet: Any) -> None:
        """Initialize trigger manager.
        
        Args:
            master: Root window
            persistence: Persistence manager instance
            telnet: Telnet manager instance
        """
        self.master = master
        self.persistence = persistence
        self.telnet = telnet
        self.triggers_window = None
        self.triggers = self.load_triggers()

    def show_window(self) -> None:
        """Display the triggers configuration window."""
        if self.triggers_window and self.triggers_window.winfo_exists():
            self.triggers_window.lift()
            return

        self.triggers_window = tk.Toplevel(self.master)
        self.triggers_window.title("Message Triggers")
        self.triggers_window.grab_set()
        
        # Create scrollable frame for triggers
        canvas = tk.Canvas(self.triggers_window)
        scrollbar = ttk.Scrollbar(self.triggers_window, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add trigger entries
        self.trigger_vars = []
        for i, trigger in enumerate(self.triggers):
            self.add_trigger_entry(i, trigger)
            
        # Add new trigger button
        ttk.Button(
            self.scrollable_frame,
            text="Add Trigger",
            command=self.add_new_trigger
        ).pack(pady=5)
        
        # Pack scrollable area
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Save button
        ttk.Button(
            self.triggers_window,
            text="Save",
            command=self.save_triggers
        ).pack(pady=10)

    def add_trigger_entry(self, index: int, trigger: Trigger) -> None:
        """Add a trigger entry to the configuration window.
        
        Args:
            index: Trigger index
            trigger: Trigger configuration
        """
        frame = ttk.LabelFrame(self.scrollable_frame, text=f"Trigger {index + 1}")
        frame.pack(fill="x", padx=5, pady=5)
        
        # Pattern entry
        ttk.Label(frame, text="Pattern:").grid(row=0, column=0, padx=5, pady=5)
        pattern_var = tk.StringVar(value=trigger.pattern)
        ttk.Entry(frame, textvariable=pattern_var).grid(row=0, column=1, padx=5, pady=5)
        
        # Response entry
        ttk.Label(frame, text="Response:").grid(row=1, column=0, padx=5, pady=5)
        response_var = tk.StringVar(value=trigger.response)
        ttk.Entry(frame, textvariable=response_var).grid(row=1, column=1, padx=5, pady=5)
        
        # Enabled checkbox
        enabled_var = tk.BooleanVar(value=trigger.enabled)
        ttk.Checkbutton(
            frame,
            text="Enabled",
            variable=enabled_var
        ).grid(row=2, column=0, columnspan=2, pady=5)
        
        self.trigger_vars.append({
            'pattern': pattern_var,
            'response': response_var,
            'enabled': enabled_var
        })

    def add_new_trigger(self) -> None:
        """Add a new empty trigger configuration."""
        self.triggers.append(Trigger("", "", True))
        self.add_trigger_entry(len(self.triggers) - 1, self.triggers[-1])

    def save_triggers(self) -> None:
        """Save trigger configurations to persistence."""
        self.triggers = [
            Trigger(
                vars['pattern'].get(),
                vars['response'].get(),
                vars['enabled'].get()
            )
            for vars in self.trigger_vars
        ]
        self.persistence.save_json(
            [vars(t) for t in self.triggers],
            'triggers.json'
        )
        self.triggers_window.destroy()

    def load_triggers(self) -> List[Trigger]:
        """Load triggers from persistence."""
        data = self.persistence.load_json('triggers.json', [])
        return [Trigger(**t) for t in data]

    def check_message(self, message: str) -> None:
        """Check message against triggers and send responses.
        
        Args:
            message: Message to check
        """
        for trigger in self.triggers:
            if not trigger.enabled:
                continue
                
            if trigger.pattern.lower() in message.lower():
                self.telnet.send(trigger.response + "\r\n")
