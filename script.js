document.getElementById("formEnvoiFacture").addEventListener("submit", async function(e) {
    e.preventDefault();

    const formData = new FormData(this);

    const response = await fetch("https://projet-final-ylci.onrender.com/sendmail", {
        method: "POST",
        body: formData
    });

    const result = await response.json();

    if (result.success) {
        alert("✅ Facture envoyée avec succès !");
    } else {
        alert("❌ Erreur : " + result.error);
    }
});
