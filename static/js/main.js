// RAOLY BTP - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            navbar.classList.toggle('scrolled', window.scrollY > 50);
        });
    }

    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Initialize all date pickers with French locale
    if (typeof flatpickr !== 'undefined') {
        flatpickr.localize(flatpickr.l10ns.fr);
        document.querySelectorAll('.datepicker:not([id])').forEach(function(el) {
            flatpickr(el, {
                locale: 'fr',
                dateFormat: 'Y-m-d',
                minDate: 'today',
            });
        });
    }

    // Cart count badge auto-update
    updateCartCount();

    // Afficher / masquer le mot de passe (formulaires auth)
    document.querySelectorAll('.password-toggle-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var group = btn.closest('.input-group');
            if (!group) return;
            var input = group.querySelector('input.form-control');
            if (!input) return;
            var icon = btn.querySelector('i');
            var show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            if (icon) {
                icon.className = show ? 'fas fa-eye-slash' : 'fas fa-eye';
            }
            btn.setAttribute('aria-label', show ? 'Masquer le mot de passe' : 'Afficher le mot de passe');
        });
    });
});

function slideCategories(direction) {
    var track = document.getElementById('categoriesTrack');
    if (track) {
        var scrollAmount = 280;
        track.scrollBy({ left: direction * scrollAmount, behavior: 'smooth' });
    }
}

function updateCartCount() {
    fetch('/panier/api/count/')
        .then(r => r.json())
        .then(data => {
            document.querySelectorAll('.badge-cart').forEach(badge => {
                if (data.count > 0) {
                    badge.textContent = data.count;
                    badge.style.display = '';
                } else {
                    badge.style.display = 'none';
                }
            });
        })
        .catch(() => {});
}
