// JARVIS Web UI - 可视化效果

class HeartbeatVisualization {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.init();
    }
    
    init() {
        this.createSVG();
        this.createCircles();
        this.startAnimation();
    }
    
    createSVG() {
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('width', '100%');
        this.svg.setAttribute('height', '100%');
        this.svg.setAttribute('viewBox', '0 0 200 200');
        this.container.appendChild(this.svg);
    }
    
    createCircles() {
        const centerX = 100;
        const centerY = 100;
        
        // 外圈 - 静态
        const outerCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        outerCircle.setAttribute('cx', centerX);
        outerCircle.setAttribute('cy', centerY);
        outerCircle.setAttribute('r', 80);
        outerCircle.setAttribute('fill', 'none');
        outerCircle.setAttribute('stroke', 'rgba(0, 212, 255, 0.3)');
        outerCircle.setAttribute('stroke-width', '2');
        this.svg.appendChild(outerCircle);
        
        // 中圈 - 旋转
        this.middleCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        this.middleCircle.setAttribute('cx', centerX);
        this.middleCircle.setAttribute('cy', centerY);
        this.middleCircle.setAttribute('r', 60);
        this.middleCircle.setAttribute('fill', 'none');
        this.middleCircle.setAttribute('stroke', 'rgba(0, 212, 255, 0.5)');
        this.middleCircle.setAttribute('stroke-width', '3');
        this.middleCircle.setAttribute('stroke-dasharray', '10, 5');
        this.svg.appendChild(this.middleCircle);
        
        // 内圈 - 心跳
        this.innerCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        this.innerCircle.setAttribute('cx', centerX);
        this.innerCircle.setAttribute('cy', centerY);
        this.innerCircle.setAttribute('r', 40);
        this.innerCircle.setAttribute('fill', 'rgba(0, 212, 255, 0.1)');
        this.innerCircle.setAttribute('stroke', 'rgba(0, 212, 255, 0.8)');
        this.innerCircle.setAttribute('stroke-width', '2');
        this.svg.appendChild(this.innerCircle);
        
        // 中心点
        const centerDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        centerDot.setAttribute('cx', centerX);
        centerDot.setAttribute('cy', centerY);
        centerDot.setAttribute('r', 5);
        centerDot.setAttribute('fill', '#00d4ff');
        this.svg.appendChild(centerDot);
        
        // 创建波纹效果
        this.rippleCircles = [];
        for (let i = 0; i < 3; i++) {
            const ripple = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            ripple.setAttribute('cx', centerX);
            ripple.setAttribute('cy', centerY);
            ripple.setAttribute('r', 40);
            ripple.setAttribute('fill', 'none');
            ripple.setAttribute('stroke', 'rgba(0, 212, 255, 0.3)');
            ripple.setAttribute('stroke-width', '1');
            ripple.style.opacity = '0';
            this.svg.appendChild(ripple);
            this.rippleCircles.push(ripple);
        }
    }
    
    startAnimation() {
        // 旋转动画
        this.middleCircle.style.animation = 'rotate 10s linear infinite';
        
        // 心跳动画
        this.innerCircle.style.animation = 'heartbeatPulse 1s ease-in-out infinite';
        
        // 波纹动画
        this.rippleCircles.forEach((ripple, index) => {
            ripple.style.animation = `ripple 2s ease-out ${index * 0.6}s infinite`;
        });
    }
}

// CSS 动画定义
const style = document.createElement('style');
style.textContent = `
    @keyframes rotate {
        from {
            transform-origin: center;
            transform: rotate(0deg);
        }
        to {
            transform-origin: center;
            transform: rotate(360deg);
        }
    }
    
    @keyframes heartbeatPulse {
        0%, 100% {
            transform-origin: center;
            transform: scale(1);
            opacity: 0.8;
        }
        50% {
            transform-origin: center;
            transform: scale(1.2);
            opacity: 1;
        }
    }
    
    @keyframes ripple {
        0% {
            transform-origin: center;
            transform: scale(1);
            opacity: 0.6;
        }
        100% {
            transform-origin: center;
            transform: scale(2.5);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 初始化心跳可视化
document.addEventListener('DOMContentLoaded', () => {
    const viz = new HeartbeatVisualization('heartbeatViz');
    window.heartbeatViz = viz;
});

// 数据波形可视化类
class WaveformVisualization {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.dataPoints = [];
        this.maxPoints = 100;
        this.animationId = null;
        
        this.init();
    }
    
    init() {
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
        this.startAnimation();
    }
    
    resizeCanvas() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
    }
    
    addDataPoint(value) {
        this.dataPoints.push(value);
        if (this.dataPoints.length > this.maxPoints) {
            this.dataPoints.shift();
        }
    }
    
    startAnimation() {
        const animate = () => {
            this.draw();
            this.animationId = requestAnimationFrame(animate);
        };
        animate();
    }
    
    draw() {
        const { width, height } = this.canvas;
        const ctx = this.ctx;
        
        ctx.clearRect(0, 0, width, height);
        
        if (this.dataPoints.length < 2) return;
        
        const gradient = ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.2)');
        gradient.addColorStop(0.5, 'rgba(0, 212, 255, 0.8)');
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0.2)');
        
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        const stepX = width / (this.maxPoints - 1);
        
        this.dataPoints.forEach((value, index) => {
            const x = index * stepX;
            const y = height - (value * height * 0.8);
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // 添加发光效果
        ctx.shadowColor = 'rgba(0, 212, 255, 0.8)';
        ctx.shadowBlur = 10;
        ctx.stroke();
        ctx.shadowBlur = 0;
    }
    
    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}

// 粒子背景效果
class ParticleBackground {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;
        
        this.particles = [];
        this.maxParticles = 50;
        this.animationId = null;
        
        this.init();
    }
    
    init() {
        this.createParticles();
        this.startAnimation();
    }
    
    createParticles() {
        for (let i = 0; i < this.maxParticles; i++) {
            const particle = {
                x: Math.random() * this.container.clientWidth,
                y: Math.random() * this.container.clientHeight,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                size: Math.random() * 2 + 1,
                opacity: Math.random() * 0.5 + 0.2
            };
            this.particles.push(particle);
        }
    }
    
    startAnimation() {
        const animate = () => {
            this.update();
            this.draw();
            this.animationId = requestAnimationFrame(animate);
        };
        animate();
    }
    
    update() {
        this.particles.forEach(particle => {
            particle.x += particle.vx;
            particle.y += particle.vy;
            
            // 边界检测
            if (particle.x < 0 || particle.x > this.container.clientWidth) {
                particle.vx *= -1;
            }
            if (particle.y < 0 || particle.y > this.container.clientHeight) {
                particle.vy *= -1;
            }
        });
    }
    
    draw() {
        // 这个方法需要在实际的 Canvas 上绘制
        // 暂时留空，可以根据需要实现
    }
    
    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}

// 导出类供外部使用
window.JarvisVisualizations = {
    HeartbeatVisualization,
    WaveformVisualization,
    ParticleBackground
};

// 粒子地球旋转动画
function initParticleGlobe() {
    const canvas = document.getElementById('globeCanvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const particles = [];
    
    // 创建粒子
    for (let i = 0; i < 50; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: Math.random() * 2 + 1,
            speedX: (Math.random() - 0.5) * 0.5,
            speedY: (Math.random() - 0.5) * 0.5,
            opacity: Math.random() * 0.5 + 0.5
        });
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // 绘制圆形背景
        ctx.beginPath();
        ctx.arc(30, 30, 28, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(0, 212, 255, 0.1)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.3)';
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // 绘制经纬线
        ctx.strokeStyle = 'rgba(0, 212, 255, 0.2)';
        ctx.lineWidth = 0.5;
        
        // 纬线
        for (let i = -2; i <= 2; i++) {
            ctx.beginPath();
            ctx.ellipse(30, 30, 28, 8, 0, 0, Math.PI * 2);
            ctx.stroke();
        }
        
        // 经线
        for (let i = 0; i < 4; i++) {
            const angle = (i * Math.PI) / 4;
            ctx.beginPath();
            ctx.ellipse(30, 30, 8, 28, angle, 0, Math.PI * 2);
            ctx.stroke();
        }
        
        // 绘制粒子
        particles.forEach(p => {
            p.x += p.speedX;
            p.y += p.speedY;
            
            // 边界检测
            const dx = p.x - 30;
            const dy = p.y - 30;
            const dist = Math.sqrt(dx * dx + dy * dy);
            
            if (dist > 25) {
                p.x = 30 + (Math.random() - 0.5) * 20;
                p.y = 30 + (Math.random() - 0.5) * 20;
            }
            
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 212, 255, ${p.opacity})`;
            ctx.fill();
        });
        
        // 中心高亮点
        const gradient = ctx.createRadialGradient(30, 30, 0, 30, 30, 15);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.8)');
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(30, 30, 15, 0, Math.PI * 2);
        ctx.fill();
        
        requestAnimationFrame(animate);
    }
    
    animate();
}

// 页面加载时初始化粒子地球
document.addEventListener('DOMContentLoaded', () => {
    initParticleGlobe();
});
