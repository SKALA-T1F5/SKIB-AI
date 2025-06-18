pipeline {
    agent any

    environment {
        GIT_URL = 'https://github.com/SKALA-T1F5/SKIB-AI.git'
        GIT_BRANCH = 'main'
        GIT_ID = 'skala-github-yoonali'
        GIT_USER_NAME = 'yoonali'
        GIT_USER_EMAIL = 'yoonalim2003@gmail.com'
        IMAGE_REGISTRY = 'amdp-registry.skala-ai.com/skala25a'
        IMAGE_NAME = 'sk-team-09-ai'
        IMAGE_TAG = '1.0.0'
        DOCKER_CREDENTIAL_ID = 'skala-image-registry-id'
    }

    stages {
        stage('Clone Repository') {
            steps {
                git branch: "${GIT_BRANCH}",
                    url: "${GIT_URL}",
                    credentialsId: "${GIT_ID}"
            }
        }

        stage('Install Python Dependencies') {
            steps {
                sh """
                    python3 -m venv venv
                    source venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                """
            }
        }

        stage('Test (Optional)') {
            steps {
                sh """
                    source venv/bin/activate
                    pytest || echo '⚠️ 테스트 실패: 무시하고 계속 진행'
                """
            }
        }

        stage('Docker Build & Push') {
            steps {
                script {
                    def hashcode = sh(script: "date +%s%N | sha256sum | cut -c1-12", returnStdout: true).trim()
                    def FINAL_IMAGE_TAG = "${IMAGE_TAG}-${BUILD_NUMBER}-${hashcode}"
                    env.FINAL_IMAGE_TAG = FINAL_IMAGE_TAG

                    docker.withRegistry("https://${IMAGE_REGISTRY}", "${DOCKER_CREDENTIAL_ID}") {
                        def appImage = docker.build("${IMAGE_REGISTRY}/${IMAGE_NAME}:${FINAL_IMAGE_TAG}", "--platform linux/amd64 .")
                        appImage.push()
                    }
                }
            }
        }

        stage('Update deploy.yaml and Git Push') {
            steps {
                script {
                    def newImageLine = "          image: ${env.IMAGE_REGISTRY}/${env.IMAGE_NAME}:${env.FINAL_IMAGE_TAG}"
                    def gitRepoPath = env.GIT_URL.replaceFirst(/^https?:\/\//, '')

                    sh """
                        sed -i 's|^[[:space:]]*image:.*\$|${newImageLine}|g' ./k8s/deploy.yaml
                        cat ./k8s/deploy.yaml
                    """

                    sh """
                        git config user.name "$GIT_USER_NAME"
                        git config user.email "$GIT_USER_EMAIL"
                        git add ./k8s/deploy.yaml || true
                    """

                    withCredentials([usernamePassword(credentialsId: "${env.GIT_ID}", usernameVariable: 'GIT_PUSH_USER', passwordVariable: 'GIT_PUSH_PASSWORD')]) {
                        sh """
                            if ! git diff --cached --quiet; then
                                git commit -m "[AUTO] Update deploy.yaml with image ${env.FINAL_IMAGE_TAG}"
                                git remote set-url origin https://${GIT_PUSH_USER}:${GIT_PUSH_PASSWORD}@${gitRepoPath}
                                git push origin ${env.GIT_BRANCH}
                            else
                                echo "No changes to commit."
                            fi
                        """
                    }
                }
            }
        }
    }
}
