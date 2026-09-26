/** @odoo-module **/

const statusBox = document.querySelector("[data-monapay-status]");

if (statusBox) {
    const poll = async () => {
        try {
            const response = await fetch(statusBox.dataset.statusUrl, {
                credentials: "same-origin",
                headers: { Accept: "application/json" },
            });
            if (response.ok) {
                const payload = await response.json();
                if (payload.state === "done" || payload.state === "authorized") {
                    statusBox.textContent = "Payment confirmed. Redirecting…";
                    window.location.assign(statusBox.dataset.returnUrl);
                    return;
                }
                if (payload.state === "error" || payload.state === "cancel") {
                    statusBox.classList.remove("alert-info");
                    statusBox.classList.add("alert-danger");
                    statusBox.textContent = "Payment could not be confirmed. Please contact the merchant.";
                    return;
                }
            }
        } catch (_error) {
            // A temporary network failure is retried by the next poll.
        }
        window.setTimeout(poll, 3000);
    };
    window.setTimeout(poll, 3000);
}

