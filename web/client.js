var pc = null;

function negotiate() {
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });
    return pc.createOffer().then((offer) => {
        return pc.setLocalDescription(offer);
    }).then(() => {
        // wait for ICE gathering to complete
        return new Promise((resolve) => {
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                const checkState = () => {
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                };
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(() => {
        var offer = pc.localDescription;
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then((response) => {
        return response.json();
    }).then((answer) => {
        document.getElementById('sessionid').value = answer.sessionid;
         // 创建一个新的RTCSessionDescription对象，只包含sdp和type
         const sessionDescription = {
            sdp: answer.sdp,
            type: answer.type
        };
        return pc.setRemoteDescription(sessionDescription);
        // 直接使用服务器返回的answer对象，不再创建新的sessionDescription对象
        // return pc.setRemoteDescription(answer);
    }).catch((e) => {
        console.error('WebRTC连接错误:', e);
        alert(e);
    });
}

function start() {
    var config = {
        sdpSemantics: 'unified-plan'
    };

    console.log('start()...');

    if (document.getElementById('use-stun').checked) {
        config.iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
    }

    pc = new RTCPeerConnection(config);

    // connect audio / video
    pc.addEventListener('track', (evt) => {
        if (evt.track.kind == 'video') {
            document.getElementById('video').srcObject = evt.streams[0];
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
        }
    });

    document.getElementById('start').style.display = 'none';
    negotiate();
    document.getElementById('stop').style.display = 'inline-block';
}

function load() {
    var config = {
        sdpSemantics: 'unified-plan'
    };

    console.log('load()函数开始执行...');
    console.log('DOM准备状态:', document.readyState);
    console.log('video元素是否存在:', !!document.getElementById('video'));
    console.log('audio元素是否存在:', !!document.getElementById('audio'));
    
    // 如果已经存在连接，先关闭它
    if (pc !== null) {
        console.log('关闭现有连接...');
        pc.close();
        pc = null;
    }
    
    // 检查视频和音频元素是否存在
    if (!document.getElementById('video') || !document.getElementById('audio')) {
        console.error('视频或音频元素不存在，无法初始化WebRTC连接');
        return;
    }
    
    console.log('创建新的RTCPeerConnection...');
    pc = new RTCPeerConnection(config);

    // 监听连接状态变化
    pc.addEventListener('connectionstatechange', () => {
        console.log('连接状态变化:', pc.connectionState);
    });
    
    // 监听ICE连接状态变化
    pc.addEventListener('iceconnectionstatechange', () => {
        console.log('ICE连接状态:', pc.iceConnectionState);
    });

    // connect audio / video
    pc.addEventListener('track', (evt) => {
        console.log('收到媒体轨道:', evt.track.kind);
        if (evt.track.kind == 'video') {
            document.getElementById('video').srcObject = evt.streams[0];
            console.log('视频轨道已连接到video元素');
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
            console.log('音频轨道已连接到audio元素');
        }
    });

    console.log('开始协商连接...');
    negotiate().catch(error => {
        console.error('WebRTC协商过程出错:', error);
    });
    console.log('load()函数执行完毕');
}

function stop() {
    document.getElementById('stop').style.display = 'none';
    document.getElementById('start').style.display = 'inline';

    // 清除视频源
    document.getElementById('video').srcObject = null;
    document.getElementById('audio').srcObject = null;

    // close peer connection
    setTimeout(() => {
        pc.close();
    }, 500);
}

window.onunload = function(event) {
    // 在这里执行你想要的操作
    setTimeout(() => {
        pc.close();
    }, 500);
};

window.onbeforeunload = function (e) {
        setTimeout(() => {
                pc.close();
            }, 500);
        e = e || window.event
        // 兼容IE8和Firefox 4之前的版本
        if (e) {
          e.returnValue = '关闭提示'
        }
        // Chrome, Safari, Firefox 4+, Opera 12+ , IE 9+
        return '关闭提示'
      }