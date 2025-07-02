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


        stage('Docker Build & Push') {
            steps {
                script {
                    // 해시코드 12자리 생성
                    def hashcode = sh(
                        script: "date +%s%N | sha256sum | cut -c1-12",
                        returnStdout: true
                    ).trim()

                    // Build Number + Hash Code 조합 (IMAGE_TAG는 유지)
                    def FINAL_IMAGE_TAG = "${IMAGE_TAG}-${BUILD_NUMBER}-${hashcode}"
                    echo "Final Image Tag: ${FINAL_IMAGE_TAG}"

                    docker.withRegistry("https://${IMAGE_REGISTRY}", "${DOCKER_CREDENTIAL_ID}") {
                        def appImage = docker.build("${IMAGE_REGISTRY}/${IMAGE_NAME}:${FINAL_IMAGE_TAG}", "--platform linux/amd64 .")
                        appImage.push()
                    }

                    // 최종 이미지 태그를 env에 등록 (나중에 deploy.yaml 수정에 사용)
                    env.FINAL_IMAGE_TAG = FINAL_IMAGE_TAG
                }
            }
        }



        stage('Update deploy.yaml and Git Push') {
            steps {
                script {
                    def newImageLine = "          image: ${env.IMAGE_REGISTRY}/${env.IMAGE_NAME}:${env.FINAL_IMAGE_TAG}"
                     // Set commands and args
                    def commandMap = [
                      'deploy.yaml'              : ['command: [\"uvicorn\"]', 'args: [\"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\", \"--limit-max-requests\", \"200\"]'],
                      'document_deploy.yaml'     : ['command: [\"celery\"]', 'args: [\"-A\", \"config.tasks\", \"worker\", \"--loglevel=info\", \"--concurrency=4\", \"-Q\", \"preprocessing_queue\"]'],
                      'test_deploy.yaml'         : ['command: [\"celery\"]', 'args: [\"-A\", \"config.tasks\", \"worker\", \"--loglevel=info\", \"--concurrency=4\", \"-Q\", \"generation_queue\"]']
                    ]

                    def yamls = ['deploy.yaml', 'document-deploy.yaml', 'test-deploy.yaml']
                    yamls.each { file ->
                        sh """
                            sed -i 's|^[[:space:]]*image:.*\$|${newImageLine}|g' ./k8s/${file}
                            sed -i '/^[[:space:]]*command:/d' ./k8s/${file}
                            sed -i '/^[[:space:]]*args:/d' ./k8s/${file}
                            sed -i '/containers:/a \\\\ \\ \\ \\ \\ ${commandMap[file][0]}\\\\n\\ \\ \\ \\ \\ ${commandMap[file][1]}' ./k8s/${file}
                            cat ./k8s/${file}
                        """
                    }

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
