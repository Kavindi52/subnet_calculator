import customtkinter as ctk
import requests
from tkinter import messagebox

BASE_URL = "http://127.0.0.1:8000"


class SubnetCalculatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("IPv4 / IPv6 & VLSM Calculator")
        self.geometry("1100x900")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.single_tab = self.tabview.add("Single Subnet")
        self.vlsm_tab   = self.tabview.add("VLSM (IPv4)")

        self._build_single_tab()
        self._build_vlsm_tab()

    def _build_single_tab(self):
        f = ctk.CTkFrame(self.single_tab)
        f.pack(padx=30, pady=20, fill="both", expand=True)
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="IP Address:", font=ctk.CTkFont(size=18)).grid(row=0, column=0, padx=15, pady=12, sticky="e")
        self.ip_entry = ctk.CTkEntry(f, placeholder_text="192.168.1.100   or   2001:db8::1", font=ctk.CTkFont(size=18), height=42)
        self.ip_entry.grid(row=0, column=1, padx=15, pady=12, sticky="ew")

        ctk.CTkLabel(f, text="Prefix / Mask:", font=ctk.CTkFont(size=18)).grid(row=1, column=0, padx=15, pady=12, sticky="e")
        self.mask_entry = ctk.CTkEntry(f, placeholder_text="24 / 64 / 255.255.255.0", font=ctk.CTkFont(size=18), height=42)
        self.mask_entry.grid(row=1, column=1, padx=15, pady=12, sticky="ew")

        btn = ctk.CTkButton(f, text="CALCULATE", font=ctk.CTkFont(size=20, weight="bold"), height=50, command=self._calc_single)
        btn.grid(row=2, column=0, columnspan=2, pady=25)

        self.single_error = ctk.CTkLabel(f, text="", text_color="#ff9800", font=ctk.CTkFont(size=16))
        self.single_error.grid(row=3, column=0, columnspan=2)

        self.single_result_frame = ctk.CTkScrollableFrame(f)
        self.single_result_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=10)
        self.single_result_frame.grid_columnconfigure(0, weight=1)
        self.single_result_frame.grid_columnconfigure(1, weight=2)

        self.single_labels = {}
        fields = [
            ("Version",           "version"),
            ("CIDR Notation",     "cidr_notation"),
            ("Network Address",   "network_address"),
            ("Prefix Length",     "prefix_length"),
            ("Subnet Mask",       "subnet_mask"),
            ("Wildcard Mask",     "wildcard_mask"),
            ("Broadcast",         "broadcast_address"),
            ("First Usable",      "first_usable"),
            ("Last Usable",       "last_usable"),
            ("Total Addresses",   "total_ips"),
            ("Usable Hosts",      "usable_hosts"),
            ("LAN Best Practice", "is_lan_recommended"),
            ("Recommendation",    "lan_recommendation_note"),
        ]

        for i, (txt, key) in enumerate(fields):
            ctk.CTkLabel(self.single_result_frame, text=f"{txt}:", font=ctk.CTkFont(size=16, weight="bold"), anchor="e").grid(
                row=i, column=0, padx=20, pady=6, sticky="e")
            val = ctk.CTkLabel(self.single_result_frame, text="───", font=ctk.CTkFont(size=16), anchor="w", wraplength=600)
            val.grid(row=i, column=1, padx=20, pady=6, sticky="w")
            self.single_labels[key] = val

    def _calc_single(self):
        addr = self.ip_entry.get().strip()
        pm   = self.mask_entry.get().strip()

        self.single_error.configure(text="")
        for v in self.single_labels.values():
            v.configure(text="───")

        if not addr or not pm:
            self.single_error.configure(text="Both fields required")
            return

        try:
            r = requests.post(f"{BASE_URL}/calculate", json={"address": addr, "prefix_or_mask": pm}, timeout=6)
            r.raise_for_status()
            data = r.json()

            for k, v in data.items():
                if k in self.single_labels:
                    lbl = self.single_labels[k]
                    if isinstance(v, bool):
                        text = "Yes – recommended for LANs" if v else "No"
                        color = "#a5d6a7" if v else "#ff9800"
                        lbl.configure(text=text, text_color=color)
                    else:
                        lbl.configure(text=str(v) if v is not None else "N/A")
        except Exception as e:
            self.single_error.configure(text=f"Error: {str(e)}")

    def _build_vlsm_tab(self):
        f = ctk.CTkFrame(self.vlsm_tab)
        f.pack(padx=30, pady=20, fill="both", expand=True)
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="Base Network (IPv4 CIDR)", font=ctk.CTkFont(size=18)).grid(row=0, column=0, padx=10, pady=12, sticky="w")
        self.vlsm_base = ctk.CTkEntry(f, placeholder_text="192.168.10.0/24 or 10.0.0.0/16", font=ctk.CTkFont(size=18), height=40)
        self.vlsm_base.grid(row=0, column=1, padx=10, pady=12, sticky="ew")

        ctk.CTkLabel(f, text="Requirements (name + hosts needed)", font=ctk.CTkFont(size=18)).grid(row=1, column=0, columnspan=3, pady=(20,10), sticky="w")

        self.vlsm_req_container = ctk.CTkScrollableFrame(f, height=280)
        self.vlsm_req_container.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=5)

        self.vlsm_rows = []  # list of (name_entry, hosts_entry, remove_btn)
        self._add_vlsm_row()  # at least one row

        add_btn = ctk.CTkButton(f, text="+ Add another subnet requirement", command=self._add_vlsm_row)
        add_btn.grid(row=3, column=0, pady=15, sticky="w")

        calc_btn = ctk.CTkButton(f, text="CALCULATE VLSM", font=ctk.CTkFont(size=20, weight="bold"), height=50, command=self._calc_vlsm)
        calc_btn.grid(row=4, column=0, columnspan=3, pady=20)

        self.vlsm_error = ctk.CTkLabel(f, text="", text_color="#ff9800", font=ctk.CTkFont(size=16))
        self.vlsm_error.grid(row=5, column=0, columnspan=3)

        self.vlsm_result = ctk.CTkScrollableFrame(f)
        self.vlsm_result.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=10)
        self.vlsm_result.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)

    def _add_vlsm_row(self):
        idx = len(self.vlsm_rows)
        name = ctk.CTkEntry(self.vlsm_req_container, placeholder_text="Dept / VLAN / link name (optional)", width=300)
        name.grid(row=idx, column=0, padx=8, pady=6)

        hosts = ctk.CTkEntry(self.vlsm_req_container, placeholder_text="usable hosts needed", width=180)
        hosts.grid(row=idx, column=1, padx=8, pady=6)

        rem = ctk.CTkButton(self.vlsm_req_container, text="Remove", width=80, fg_color="#d32f2f", hover_color="#b71c1c",
                             command=lambda i=idx: self._remove_vlsm_row(i))
        rem.grid(row=idx, column=2, padx=8, pady=6)

        self.vlsm_rows.append((name, hosts, rem))

    def _remove_vlsm_row(self, idx):
        if len(self.vlsm_rows) <= 1:
            return
        for w in self.vlsm_rows[idx]:
            w.destroy()
        self.vlsm_rows.pop(idx)

        # re-index remove buttons
        for i, (_, _, rem_btn) in enumerate(self.vlsm_rows):
            rem_btn.configure(command=lambda x=i: self._remove_vlsm_row(x))

        # re-grid
        for i, (n, h, r) in enumerate(self.vlsm_rows):
            n.grid(row=i, column=0, padx=8, pady=6)
            h.grid(row=i, column=1, padx=8, pady=6)
            r.grid(row=i, column=2, padx=8, pady=6)

    def _calc_vlsm(self):
        base = self.vlsm_base.get().strip()
        if not base:
            self.vlsm_error.configure(text="Base network is required")
            return

        reqs = []
        for name_e, hosts_e, _ in self.vlsm_rows:
            name = name_e.get().strip()
            try:
                h = int(hosts_e.get().strip())
                if h > 0:
                    reqs.append({"name": name, "hosts": h})
            except:
                pass

        if not reqs:
            self.vlsm_error.configure(text="Enter at least one valid host count")
            return

        self.vlsm_error.configure(text="")
        for w in self.vlsm_result.winfo_children():
            w.destroy()

        try:
            resp = requests.post(f"{BASE_URL}/vlsm", json={"base_network": base, "requirements": reqs}, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            row = 0
            if data.get("warning"):
                ctk.CTkLabel(self.vlsm_result, text=data["warning"], text_color="yellow").grid(row=row, column=0, columnspan=7, pady=8)
                row += 1

            headers = ["Name", "Req. Hosts", "Assigned", "Usable", "Network", "First", "Last"]
            for col, txt in enumerate(headers):
                ctk.CTkLabel(self.vlsm_result, text=txt, font=ctk.CTkFont(weight="bold")).grid(row=row, column=col, padx=10, pady=6, sticky="ew")
            row += 1

            for ass in data["assignments"]:
                values = [
                    ass["name"],
                    str(ass["required_hosts"]),
                    ass["assigned_cidr"],
                    str(ass["usable_hosts"]),
                    ass["network_address"],
                    ass["first_usable"],
                    ass["last_usable"]
                ]
                for col, val in enumerate(values):
                    ctk.CTkLabel(self.vlsm_result, text=val, wraplength=160).grid(row=row, column=col, padx=10, pady=4, sticky="ew")
                row += 1

            if data["remaining_networks"]:
                ctk.CTkLabel(self.vlsm_result, text="Remaining space:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, columnspan=2, pady=12, sticky="w")
                ctk.CTkLabel(self.vlsm_result, text="  •  " + "  •  ".join(data["remaining_networks"])).grid(row=row, column=2, columnspan=5, pady=12, sticky="w")

        except Exception as e:
            self.vlsm_error.configure(text=f"Error: {str(e)}")


if __name__ == "__main__":
    app = SubnetCalculatorApp()
    app.mainloop()