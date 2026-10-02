pipeline {
    agent any

    options {
        // 保留最近 10 次构建
        buildDiscarder(logRotator(numToKeepStr: '10'))
        // 禁止并发构建
        disableConcurrentBuilds()
        // 超时保护：15 分钟
        timeout(time: 15, unit: 'MINUTES')
        // 每行日志带时间戳
        timestamps()
    }

    environment {
        CI = 'true'
        FLASK_DEBUG = '0'
        VENV_DIR = '.venv'
    }

    stages {
        stage('Checkout') {
            steps {
                echo '[1/6] 拉取代码...'
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                echo '[2/6] 准备 Python 环境...'
                sh '''
                    python3 --version
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                echo '[3/6] 安装依赖...'
                sh '''
                    . ${VENV_DIR}/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo '[4/6] 执行测试 + 覆盖率...'
                sh '''
                    . ${VENV_DIR}/bin/activate
                    python -m pytest
                '''
            }
            post {
                always {
                    // 归档 JUnit，让 Jenkins 显示测试趋势图
                    junit allowEmptyResults: true,
                          testResults: 'test-results/junit.xml'
                }
            }
        }

        stage('Quality Gate') {
            steps {
                echo '[5/6] 执行质量门禁...'
                sh '''
                    . ${VENV_DIR}/bin/activate
                    python scripts/quality_gate.py --threshold 90
                '''
            }
        }

        stage('Archive Reports') {
            steps {
                echo '[6/6] 归档报告...'
                sh '''
                    . ${VENV_DIR}/bin/activate
                    python scripts/scorer.py || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/**/*',
                                     allowEmptyArchive: true,
                                     fingerprint: true
                    archiveArtifacts artifacts: 'allure-results/**/*',
                                     allowEmptyArchive: true
                }
            }
        }
    }

    post {
        success {
            echo '✅ 流水线成功，所有测试通过。'
        }
        failure {
            echo '❌ 流水线失败，请检查测试日志。'
        }
        always {
            sh 'rm -rf ${VENV_DIR} || true'
        }
    }
}