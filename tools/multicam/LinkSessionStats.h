#pragma once
#include "SessionState.h"
#include "MAVLinkMessageType.h"
#include <QtCore/QElapsedTimer>
#include <QtCore/QPointer>
#include <QtCore/QTimer>
#include <QtQmlIntegration/QtQmlIntegration>
class Vehicle;
class LinkInterface;
class VideoManager;

class LinkSessionStats : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("")
    Q_PROPERTY(double trafficMB READ trafficMB NOTIFY changed)
    Q_PROPERTY(int pingMs READ pingMs NOTIFY changed)
    Q_PROPERTY(bool connected READ connected NOTIFY changed)
public:
    explicit LinkSessionStats(VideoManager *parent);
    double trafficMB() const { return _session.bytes / 1000000.0; }
    int pingMs() const { return _pingMs; }
    bool connected() const;
    void addVideoBytes(quint64 amount);
signals:
    void changed();
private:
    void setVehicle(Vehicle *vehicle);
    void tick();
    void received(LinkInterface *link, const mavlink_message_t &message);
    QString identity() const;
    void reset();
    VideoManager *_video;
    QPointer<Vehicle> _vehicle;
    QElapsedTimer _clock;
    QTimer _timer;
    SessionState _session;
    qint64 _lastReceived = 0;
    qint64 _lastPingSent = -1;
    qint64 _lastPingReply = -1;
    quint64 _pingStamp = 0;
    quint32 _pingSeq = 0;
    int _pingMs = -1;
};
