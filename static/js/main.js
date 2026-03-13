function copyLink(url) {
    if (!navigator.clipboard) {
        window.prompt("Copy this link:", url);
        return;
    }
    navigator.clipboard.writeText(url).then(function () {
        alert("Product link copied.");
    });
}

function shareProduct(title, url) {
    if (navigator.share) {
        navigator.share({
            title: title,
            url: url,
        });
    } else {
        copyLink(url);
    }
}

window.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".product-card, .glass-card, .hero-panel").forEach(function (node, idx) {
        node.style.opacity = 0;
        node.style.transform = "translateY(10px)";
        setTimeout(function () {
            node.style.transition = "opacity 0.45s ease, transform 0.45s ease";
            node.style.opacity = 1;
            node.style.transform = "translateY(0)";
        }, 35 * idx);
    });
});
