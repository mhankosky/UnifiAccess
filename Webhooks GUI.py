import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json

# API Configuration
API_TOKEN = "API KEY"  # Your API token
HOSTNAME = "https://172.18.1.1:12445"   # Your hostname
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Predefined list of supported webhook events from UniFi Access API (section 11.2)
WEBHOOK_EVENTS = [
    "access.doorbell.incoming",
    "access.doorbell.completed",
    "access.doorbell.incoming.REN",
    "access.device.dps_status",
    "access.door.unlock",
    "access.device.emergency_status"
]

class WebhookManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UniFi Access Webhook Manager")
        self.root.geometry("800x600")

        # Frame for Webhook List
        self.list_frame = ttk.Frame(root)
        self.list_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        # Webhook Listbox with Scrollbar
        self.webhook_list = ttk.Treeview(self.list_frame, columns=("ID", "Name", "Endpoint", "Events"), show="headings")
        self.webhook_list.heading("ID", text="ID")
        self.webhook_list.heading("Name", text="Name")
        self.webhook_list.heading("Endpoint", text="Endpoint")
        self.webhook_list.heading("Events", text="Events")
        self.webhook_list.column("ID", width=150)
        self.webhook_list.column("Name", width=150)
        self.webhook_list.column("Endpoint", width=200)
        self.webhook_list.column("Events", width=250)
        self.webhook_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.webhook_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.webhook_list.configure(yscrollcommand=scrollbar.set)

        # Buttons Frame
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(pady=10)

        ttk.Button(self.button_frame, text="Refresh", command=self.refresh_webhooks).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Add", command=self.add_webhook).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Edit", command=self.edit_webhook).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Delete", command=self.delete_webhook).pack(side=tk.LEFT, padx=5)

        # Initial Load
        self.refresh_webhooks()

    def refresh_webhooks(self):
        """Fetch and display all webhook endpoints."""
        self.webhook_list.delete(*self.webhook_list.get_children())
        try:
            response = requests.get(f"{HOSTNAME}/api/v1/developer/webhooks/endpoints", headers=HEADERS, verify=False)
            response.raise_for_status()
            data = response.json()
            if data["code"] == "SUCCESS":
                for webhook in data["data"]:
                    self.webhook_list.insert("", "end", values=(
                        webhook["id"],
                        webhook["name"],
                        webhook["endpoint"],
                        ", ".join(webhook["events"])
                    ))
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to fetch webhooks: {e}")

    def add_webhook(self):
        """Open a window to add a new webhook."""
        self._open_webhook_form("Add Webhook", self._save_new_webhook)

    def edit_webhook(self):
        """Open a window to edit the selected webhook."""
        selected = self.webhook_list.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a webhook to edit.")
            return
        webhook_id = self.webhook_list.item(selected[0])["values"][0]
        self._open_webhook_form("Edit Webhook", self._save_edited_webhook, webhook_id)

    def delete_webhook(self):
        """Delete the selected webhook."""
        selected = self.webhook_list.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a webhook to delete.")
            return
        webhook_id = self.webhook_list.item(selected[0])["values"][0]
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete webhook {webhook_id}?"):
            try:
                response = requests.delete(
                    f"{HOSTNAME}/api/v1/developer/webhooks/endpoints/{webhook_id}",
                    headers=HEADERS,
                    verify=False
                )
                response.raise_for_status()
                if response.json()["code"] == "SUCCESS":
                    messagebox.showinfo("Success", "Webhook deleted successfully.")
                    self.refresh_webhooks()
            except requests.RequestException as e:
                messagebox.showerror("Error", f"Failed to delete webhook: {e}")

    def _open_webhook_form(self, title, save_callback, webhook_id=None):
        """Open a form for adding or editing a webhook."""
        form = tk.Toplevel(self.root)
        form.title(title)
        form.geometry("400x400")

        # Name Field
        ttk.Label(form, text="Name:").pack(pady=5)
        name_entry = ttk.Entry(form)
        name_entry.pack(pady=5)

        # Endpoint Field
        ttk.Label(form, text="Endpoint (HTTPS URL):").pack(pady=5)
        endpoint_entry = ttk.Entry(form)
        endpoint_entry.pack(pady=5)

        # Events Multi-Select Dropdown
        ttk.Label(form, text="Events (Select multiple):").pack(pady=5)
        events_listbox = tk.Listbox(form, selectmode=tk.MULTIPLE, height=10)
        for event in WEBHOOK_EVENTS:
            events_listbox.insert(tk.END, event)
        events_listbox.pack(pady=5)

        # Pre-fill form if editing
        if webhook_id:
            try:
                response = requests.get(
                    f"{HOSTNAME}/api/v1/developer/webhooks/endpoints",
                    headers=HEADERS,
                    verify=False
                )
                webhooks = response.json()["data"]
                webhook = next(w for w in webhooks if w["id"] == webhook_id)
                name_entry.insert(0, webhook["name"])
                endpoint_entry.insert(0, webhook["endpoint"])
                # Pre-select events in the listbox
                for i, event in enumerate(WEBHOOK_EVENTS):
                    if event in webhook["events"]:
                        events_listbox.select_set(i)
            except requests.RequestException as e:
                messagebox.showerror("Error", f"Failed to load webhook data: {e}")
                form.destroy()
                return

        # Save Button
        ttk.Button(form, text="Save", command=lambda: save_callback(
            form, name_entry.get(), endpoint_entry.get(), 
            [WEBHOOK_EVENTS[i] for i in events_listbox.curselection()], webhook_id
        )).pack(pady=10)

    def _save_new_webhook(self, form, name, endpoint, events, _):
        """Save a new webhook."""
        if not events:
            messagebox.showwarning("Warning", "Please select at least one event.")
            return
        payload = {
            "name": name,
            "endpoint": endpoint,
            "events": events
        }
        try:
            response = requests.post(
                f"{HOSTNAME}/api/v1/developer/webhooks/endpoints",
                headers=HEADERS,
                json=payload,
                verify=False
            )
            response.raise_for_status()
            if response.json()["code"] == "SUCCESS":
                messagebox.showinfo("Success", "Webhook added successfully.")
                self.refresh_webhooks()
                form.destroy()
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to add webhook: {e}")

    def _save_edited_webhook(self, form, name, endpoint, events, webhook_id):
        """Save changes to an existing webhook."""
        if not events:
            messagebox.showwarning("Warning", "Please select at least one event.")
            return
        payload = {
            "name": name,
            "endpoint": endpoint,
            "events": events
        }
        try:
            response = requests.put(
                f"{HOSTNAME}/api/v1/developer/webhooks/endpoints/{webhook_id}",
                headers=HEADERS,
                json=payload,
                verify=False
            )
            response.raise_for_status()
            if response.json()["code"] == "SUCCESS":
                messagebox.showinfo("Success", "Webhook updated successfully.")
                self.refresh_webhooks()
                form.destroy()
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to update webhook: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WebhookManagerApp(root)
    root.mainloop()