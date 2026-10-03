#include "LinkSessionStats.h"
#include "VideoManager.h"
#include "MultiVehicleManager.h"
#include "MAVLinkProtocol.h"
#include "LinkManager.h"
#include "Vehicle.h"
#include "VehicleLinkManager.h"
#include "LinkConfiguration.h"

LinkSessionStats::LinkSessionStats(VideoManager *parent) : QObject(parent), _video(parent) {
    _clock.start();
    connect(MultiVehicleManager::instance(), &MultiVehicleManager::activeVehicleChanged,
            this, &LinkSessionStats::setVehicle);
    connect(MAVLinkProtocol::instance(), &MAVLinkProtocol::messageReceived,
            this, &LinkSessionStats::received);
    connect(MAVLinkProtocol::instance(), &MAVLinkProtocol::receivedByteCount, this,
            [this](LinkInterface *link, qint64 amount) {
        if (_vehicle && _vehicle->vehicleLinkManager()->containsLink(link)) {
            _session.add(static_cast<quint64>(amount), _clock.elapsed());
        }
    });
    connect(LinkManager::instance(), &LinkManager::userDisconnectRequested, this,
            [this](LinkInterface *link) {
        if (!link || (_vehicle && _vehicle->vehicleLinkManager()->containsLink(link))) reset();
    });
    _timer.setInterval(1000);
    connect(&_timer, &QTimer::timeout, this, &LinkSessionStats::tick);
    _timer.start();
    setVehicle(MultiVehicleManager::instance()->activeVehicle());
}

bool LinkSessionStats::connected() const {
    return _vehicle && !_vehicle->vehicleLinkManager()->communicationLost();
}

QString LinkSessionStats::identity() const {
    if (!_vehicle) return QString();
    const auto link = _vehicle->vehicleLinkManager()->primaryLink().lock();
    const QString name = link ? link->linkConfiguration()->name() : QString();
    return QStringLiteral("%1:%2").arg(_vehicle->id()).arg(name);
}

void LinkSessionStats::reset() {
    _video->takeReceivedVideoBytes();
    _session.disconnect();
    _pingMs = -1;
    _lastPingSent = _lastPingReply = -1;
    emit changed();
}

void LinkSessionStats::setVehicle(Vehicle *vehicle) {
    _video->takeReceivedVideoBytes();
    if (_vehicle) {
        disconnect(_vehicle->vehicleLinkManager(), nullptr, this, nullptr);
        disconnect(_vehicle, nullptr, this, nullptr);
    }
    if (!vehicle) _session.lost(_lastReceived);
    _vehicle = vehicle;
    _pingMs = -1;
    _lastPingSent = _lastPingReply = -1;
    if (_vehicle) {
        connect(_vehicle, &Vehicle::userDisconnectRequested, this, &LinkSessionStats::reset);
        _session.connect(identity().toStdString(), _clock.elapsed());
        _lastReceived = _clock.elapsed();
        connect(_vehicle->vehicleLinkManager(), &VehicleLinkManager::communicationLostChanged,
                this, [this](bool lost) {
            _video->takeReceivedVideoBytes();
            if (lost) {
                _session.lost(_lastReceived);
                _pingMs = -1;
                _lastPingSent = _lastPingReply = -1;
            } else {
                _session.connect(identity().toStdString(), _clock.elapsed());
                _lastReceived = _clock.elapsed();
            }
            emit changed();
        });
    }
    emit changed();
}

void LinkSessionStats::addVideoBytes(quint64 amount) {
    _session.add(amount, _clock.elapsed());
}

void LinkSessionStats::received(LinkInterface *link, const mavlink_message_t &message) {
    if (!_vehicle || message.sysid != _vehicle->id() || !_vehicle->vehicleLinkManager()->containsLink(link)) return;
    const qint64 now = _clock.elapsed();
    _video->takeReceivedVideoBytes();
    if (_session.gapStart >= 0) _session.connect(identity().toStdString(), now);
    _lastReceived = now;
    if (message.msgid != MAVLINK_MSG_ID_PING) return;
    const auto primary = _vehicle->vehicleLinkManager()->primaryLink().lock();
    if (!primary || primary.get() != link || message.compid != _vehicle->defaultComponentId()) return;
    mavlink_ping_t ping{};
    mavlink_msg_ping_decode(&message, &ping);
    if (ping.target_system != MAVLinkProtocol::instance()->getSystemId() ||
        ping.target_component != MAVLinkProtocol::getComponentId() ||
        ping.seq != _pingSeq || ping.time_usec != _pingStamp || _lastPingSent < 0) return;
    _lastPingReply = _clock.elapsed();
    _pingMs = static_cast<int>(_lastPingReply - _lastPingSent);
    emit changed();
}

void LinkSessionStats::tick() {
    const qint64 now = _clock.elapsed();
    // Detect silence from the last data, independent of QGC's heartbeat grace.
    if (_vehicle && now - _lastReceived > 3500) _session.lost(_lastReceived);
    _video->takeReceivedVideoBytes();
    if (_lastPingReply < 0 || now - _lastPingReply > 5000) _pingMs = -1;
    if (connected() && (_lastPingSent < 0 || now - _lastPingSent >= 2000)) {
        const auto link = _vehicle->vehicleLinkManager()->primaryLink().lock();
        if (link) {
            _lastPingSent = now;
            _pingStamp = static_cast<quint64>(now) * 1000;
            ++_pingSeq;
            mavlink_message_t message{};
            mavlink_msg_ping_pack_chan(static_cast<uint8_t>(MAVLinkProtocol::instance()->getSystemId()),
                static_cast<uint8_t>(MAVLinkProtocol::getComponentId()), link->mavlinkChannel(),
                &message, _pingStamp, _pingSeq, 0, 0);
            _vehicle->sendMessageOnLinkThreadSafe(link.get(), message);
        }
    }
    emit changed();
}
