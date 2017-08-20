#!/usr/bin/env python
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import rospy
import tf
from beacon_msgs.srv import GetBeaconDistances
from geometry_msgs.msg import Pose, Point
from scripts.basic_trilateration import BasicTrilaterationEngine


def get_param(name, default_val):
    try:
        return rospy.get_param(name)
    except KeyError:
        return default_val


if __name__ == "__main__":
    # init ros
    rospy.init_node('trilateration')
    rospy.loginfo("Starting Trilateration node")

    TAG_DISTANCE_FILTERING = get_param('beacon_listener/trilateration/distance_filtering', 'recent')
    LOCALIZATION_RATE = get_param('beacon_listener/trilateration/localization_rate', 1)
    TRILATERATION_ENGINE = get_param('beacon_listener/trilateration/engine', 'basic')

    rospy.loginfo("Filtering: %s", TAG_DISTANCE_FILTERING)
    rospy.loginfo("Engine: %s", TRILATERATION_ENGINE)


    # Create engine
    trilateration_engine = None
    if TRILATERATION_ENGINE is 'basic':
        trilateration_engine = BasicTrilaterationEngine()
    if TRILATERATION_ENGINE is 'iterative':
        raise RuntimeError('Iterative Trilateration Engine is not implemented yet')
        # trilateration_engine = IterativeTrilaterationEngine()

    # Setup service
    service_path = '/beacon_localization/distances/' + TAG_DISTANCE_FILTERING
    rospy.wait_for_service(service_path)
    get_beacons_srv = rospy.ServiceProxy(service_path, GetBeaconDistances)

    # Setup tf broadcaster and pose publisher
    br = tf.TransformBroadcaster()
    pub = rospy.Publisher('/beacon_localization/bl_pose', Pose, queue_size=100)

    r = rospy.Rate(LOCALIZATION_RATE)
    while not rospy.is_shutdown():
        # Ask for beacons
        beacons_with_distances = get_beacons_srv.call()
        # Do trilateration
        if len(beacons_with_distances.measurements) < 3:
            rospy.logwarn('Insufficient measurements for trilateration: %s', len(beacons_with_distances.measurements))
            pass
        position = trilateration_engine.calculate(beacons_with_distances.measurements)

        pub.publish(Pose(position=Point(
            x=position[0],
            y=position[1],
            z=position[2]
        )))

        br.sendTransform(
            (position[0], position[1], position[2]),
            tf.transformations.quaternion_from_euler(0, 0, 0),
            rospy.Time.now(),
            'bl_pose',
            'map'
        )

        r.sleep()

