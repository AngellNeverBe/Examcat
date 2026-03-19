/*
版权声明：本文为CSDN博主「@才华有限公司」的原创文章，遵循CC 4.0 BY-SA版权协议，转载请附上原文出处链接及本声明。
原文链接：https://blog.csdn.net/gentleman_hua/article/details/147645833
 */

// 容器
document.getElementById('confetti-button').onclick = createConfetti

// 页面加载后自动触发一次彩带效果
window.onload = function () {
    setTimeout(createConfetti, 500)
}

function createConfetti() {
    // 清除现有彩带
    const container = document.getElementById('confetti-container')
    container.innerHTML = ''

    // 彩带颜色
    const colors = [
        '#f44336',
        '#e91e63',
        '#9c27b0',
        '#673ab7',
        '#3f51b5',
        '#2196f3',
        '#03a9f4',
        '#00bcd4',
        '#009688',
        '#4CAF50',
        '#8BC34A',
        '#CDDC39',
        '#FFEB3B',
        '#FFC107',
        '#FF9800',
        '#FF5722',
    ]

    // 物理参数 - 烟花效果
    const gravity = 0.25 // 重力加速度 - 增强
    const initialVelocity = 20 // 基础初始速度 - 显著提高
    const velocityVariation = 8 // 速度变化幅度
    const dragCoefficient = 0.98 // 阻力系数 - 稍微增加以模拟空气阻力

    // 创建彩带 - 增加数量以创造更密集的效果
    for (let i = 0; i < 200; i++) {
        setTimeout(function () {
        const confetti = document.createElement('div')
        confetti.className = 'confetti'

        // 随机彩带特性
        const color = colors[Math.floor(Math.random() * colors.length)]
        const shape =
            Math.random() < 0.33 ? 'circle' : Math.random() < 0.66 ? 'rectangle' : 'triangle'
        const size = Math.random() * 10 + 5

        // 从两侧喷出 - 随机选择左侧或右侧
        const side = Math.random() < 0.5 ? 'left' : 'right'
        const xPos = side === 'left' ? 0 : window.innerWidth
        const yPos = window.innerHeight * 0.8 + Math.random() * window.innerHeight * 0.2 // 更靠近底部发射

        // 角度设置 - 更多向上的角度，像烟花发射
        let angle
        if (side === 'left') {
            angle = -Math.PI / 2 + (Math.random() * Math.PI) / 4 // -90度到-45度（强烈向上偏右）
        } else {
            angle = (Math.PI * 3) / 2 - (Math.random() * Math.PI) / 4 // 225度到270度（强烈向上偏左）
        }

        // 初始速度 - 更高的初速度模拟烟花发射
        const velocity = initialVelocity + Math.random() * velocityVariation

        // 设置初始位置和样式
        confetti.style.left = xPos + 'px'
        confetti.style.top = yPos + 'px'
        confetti.style.width = size + 'px'
        confetti.style.height = size + 'px'
        confetti.style.backgroundColor = color
        confetti.style.transform = 'rotate(' + Math.random() * 360 + 'deg)'

        // 设置不同形状
        if (shape === 'circle') {
            confetti.style.borderRadius = '50%'
        } else if (shape === 'triangle') {
            confetti.style.width = '0'
            confetti.style.height = '0'
            confetti.style.backgroundColor = 'transparent'
            confetti.style.borderLeft = size / 2 + 'px solid transparent'
            confetti.style.borderRight = size / 2 + 'px solid transparent'
            confetti.style.borderBottom = size + 'px solid ' + color
        }

        container.appendChild(confetti)

        // 动画参数
        let xVelocity = Math.cos(angle) * velocity
        let yVelocity = Math.sin(angle) * velocity
        const rotateVel = Math.random() * 0.2 - 0.1
        let rotation = Math.random() * 360

        // 时间跟踪（毫秒）
        let time = 0
        const initialBurstDuration = 500 // 初始高速喷射持续500毫秒
        let lastTimestamp = performance.now()

        // 动画函数
        function animate(timestamp) {
            // 计算时间差
            const deltaTime = timestamp - lastTimestamp
            lastTimestamp = timestamp
            time += deltaTime

            // 应用物理效果
            if (time < initialBurstDuration) {
            // 初始爆发阶段 - 保持高速，稍微减速
            yVelocity *= 0.99
            xVelocity *= 0.99
            } else {
            // 自由落体阶段
            yVelocity += gravity
            xVelocity *= dragCoefficient
            }

            // 更新位置
            const currentX = parseFloat(confetti.style.left)
            const currentY = parseFloat(confetti.style.top)
            confetti.style.left = currentX + xVelocity + 'px'
            confetti.style.top = currentY + yVelocity + 'px'

            // 旋转彩带
            rotation += rotateVel
            confetti.style.transform = 'rotate(' + rotation + 'deg)'

            // 超出屏幕移除彩带
            if (
            currentY < window.innerHeight + 100 &&
            currentX > -100 &&
            currentX < window.innerWidth + 100
            ) {
            requestAnimationFrame(animate)
            } else {
            confetti.remove()
            }
        }

        // 启动动画
        requestAnimationFrame(animate)
        }, Math.random() * 800) // 缩短发射间隔，使效果更集中
    }
}
