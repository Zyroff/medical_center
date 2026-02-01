document.addEventListener('DOMContentLoaded', function() {
    
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navList = document.querySelector('.nav-list');
    const mobileOverlay = document.querySelector('.mobile-overlay');
    
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', () => {
            navList.classList.toggle('active');
            mobileOverlay.classList.toggle('active');
            document.body.style.overflow = navList.classList.contains('active') ? 'hidden' : 'auto';
        });
    }
    
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', () => {
            navList.classList.remove('active');
            mobileOverlay.classList.remove('active');
            document.body.style.overflow = 'auto';
        });
    }
    
    const scrollToTopBtn = document.querySelector('.scroll-to-top');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            scrollToTopBtn.classList.add('visible');
        } else {
            scrollToTopBtn.classList.remove('visible');
        }
    });
    
    if (scrollToTopBtn) {
        scrollToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
    
    document.querySelectorAll('.alert-close').forEach(button => {
        button.addEventListener('click', function() {
            const alert = this.closest('.alert');
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.style.display = 'none';
            }, 300);
        });
    });
    
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.style.display = 'none';
            }, 300);
        });
    }, 5000);
    
    function setActiveNavLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const linkPath = link.getAttribute('href');
            if (linkPath && currentPath === linkPath) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }
    
    setActiveNavLink();
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.feature-card, .doctor-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        observer.observe(el);
    });
    
    const animationStyle = document.createElement('style');
    animationStyle.textContent = `
        .feature-card.animated,
        .doctor-card.animated {
            animation: fadeIn 0.6s ease forwards;
        }
        
        @keyframes fadeIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(animationStyle);
    
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            if (href === '#' || !href.startsWith('#') || href === '#map') {
                return;
            }
            
            e.preventDefault();
            const targetElement = document.querySelector(href);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
                
                if (navList.classList.contains('active')) {
                    navList.classList.remove('active');
                    mobileOverlay.classList.remove('active');
                    document.body.style.overflow = 'auto';
                }
            }
        });
    });
    
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
                submitBtn.disabled = true;
            }
        });
    });
    
    function updateBusinessHours() {
        const now = new Date();
        const hour = now.getHours();
        const day = now.getDay();
        
        const isWorkingHours = (day >= 1 && day <= 5 && hour >= 8 && hour < 20) ||
                              ((day === 0 || day === 6) && hour >= 9 && hour < 18);
        
        const statusElement = document.querySelector('.working-status');
        if (statusElement) {
            if (isWorkingHours) {
                statusElement.innerHTML = '<i class="fas fa-check-circle" style="color: #00c9a7"></i> Сейчас работаем';
            } else {
                statusElement.innerHTML = '<i class="fas fa-clock" style="color: #ff6b6b"></i> Сейчас закрыто';
            }
        }
    }
    
    updateBusinessHours();
    setInterval(updateBusinessHours, 60000);
    
});